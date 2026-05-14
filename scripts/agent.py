"""agent.py — BID-IA Literature Review Agent

Agentic CLI: Claude (Sonnet) orchestrates the pipeline, deciding which tools to call.
Sub-calls to Claude Haiku execute actual AI review and synthesis.
Search covers 9 sources: Semantic Scholar, NBER, OpenAlex, ArXiv, SSRN,
PubMed, CORE, World Bank, IMF.

Usage:
  python scripts/agent.py --status
  python scripts/agent.py --pocket labor
  python scripts/agent.py --pocket evaluacion_experimental --mode search
  python scripts/agent.py "what gaps exist in our current corpus?"
  python scripts/agent.py --interactive
"""

import anthropic
import argparse
import difflib
import hashlib
import json
import logging
import os
import re
import sys
import time
import textwrap
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pockets import POCKETS, RUBRIC, PROJECT_CONTEXT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("agent")

ROOT = Path(__file__).parent.parent


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config.json from repo root, or return safe defaults."""
    cfg_path = ROOT / "config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text())
        except Exception as e:
            log.warning(f"Could not parse config.json: {e}")
    return {}


CONFIG = load_config()

def _cfg_key(name: str) -> str:
    """Read API key: config.json api_keys.name → env var → empty string."""
    val = CONFIG.get("api_keys", {}).get(name, "")
    if not val:
        val = os.environ.get(name.upper(), "")
    return val


# ── Search cache ──────────────────────────────────────────────────────────────

CACHE_FILE = ROOT / "search_cache.json"
CACHE_TTL_HOURS = CONFIG.get("search_cache_ttl_hours", 24)


def _cache_key(pocket: str, source: str, query: str, extras: dict = None) -> str:
    payload = json.dumps(
        {"pocket": pocket, "source": source, "query": query, **(extras or {})},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _cache_get(key: str) -> list | None:
    if not CACHE_FILE.exists():
        return None
    try:
        store = json.loads(CACHE_FILE.read_text())
    except Exception:
        return None
    entry = store.get(key)
    if not entry:
        return None
    ts = datetime.fromisoformat(entry["timestamp"])
    age_hours = (datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    if age_hours > CACHE_TTL_HOURS:
        return None
    return entry["results"]


def _cache_set(key: str, results: list) -> None:
    store = {}
    if CACHE_FILE.exists():
        try:
            store = json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    store[key] = {"timestamp": datetime.now(timezone.utc).isoformat(), "results": results}
    CACHE_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2))


# ── Safe execute wrapper ──────────────────────────────────────────────────────

def safe_execute_tool(tool_fn, *args, max_retries: int = 3, backoff: int = 2, tool_name: str = ""):
    """Retry wrapper with exponential backoff. Returns error dict on final failure."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return tool_fn(*args)
        except Exception as e:
            last_exc = e
            wait = backoff ** attempt
            log.warning(f"[{tool_name}] attempt {attempt+1}/{max_retries} failed: {e}. Retrying in {wait}s")
            time.sleep(wait)
    log.warning(f"[{tool_name}] all {max_retries} attempts failed: {last_exc}")
    return [{"error": True, "tool": tool_name, "reason": str(last_exc)}]


# ── Search helpers ────────────────────────────────────────────────────────────

_PAPER_KEYS = ("title", "authors", "year", "abstract", "url", "doi", "source",
               "full_text_url", "venue", "citations")


def _normalize_paper(p: dict) -> dict:
    """Ensure every paper has the canonical contract keys."""
    return {k: p.get(k, "" if k not in ("year", "citations") else None) for k in _PAPER_KEYS}


def _search_semantic_scholar(query: str, limit: int, year_start: int) -> list:
    import requests
    BASE = "https://api.semanticscholar.org/graph/v1"
    FIELDS = "paperId,title,abstract,authors,year,venue,citationCount,externalIds,openAccessPdf"
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS, "year": f"{year_start}-"}
    r = requests.get(f"{BASE}/paper/search", params=params, timeout=15)
    if r.status_code == 429:
        time.sleep(10)
        r = requests.get(f"{BASE}/paper/search", params=params, timeout=15)
    r.raise_for_status()
    results = []
    for p in r.json().get("data", []):
        if not p.get("title"):
            continue
        authors_list = p.get("authors") or []
        authors = ", ".join(a.get("name", "") for a in authors_list[:4])
        if len(authors_list) > 4:
            authors += " et al."
        ids = p.get("externalIds") or {}
        doi = ids.get("DOI", "")
        arxiv_id = ids.get("ArXiv", "")
        pdf = (p.get("openAccessPdf") or {}).get("url", "")
        url = pdf or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else
                      f"https://doi.org/{doi}" if doi else "")
        results.append({
            "title": p.get("title", ""),
            "authors": authors,
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "abstract": p.get("abstract", ""),
            "url": url,
            "doi": doi,
            "full_text_url": pdf,
            "citations": p.get("citationCount", 0),
            "source": "semantic_scholar",
        })
    return results


def _search_nber(query: str, limit: int) -> list:
    import requests
    r = requests.get(
        "https://www.nber.org/api/v1/search",
        params={"q": query, "type": "working_paper", "start": 0,
                "perPage": min(limit, 30)},
        timeout=15, headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    results = []
    for p in r.json().get("results", []):
        # skip author/entity results
        if p.get("type") == "entity:user" or not p.get("title"):
            continue
        # authors is a list of HTML anchor strings — strip tags to get names
        authors_list = p.get("authors") or []
        def _strip_html(s):
            return re.sub(r"<[^>]+>", "", str(s)).strip()
        authors = ", ".join(_strip_html(a) for a in authors_list[:4])
        m = re.search(r"(\d{4})", str(p.get("displaydate") or p.get("publisheddate") or ""))
        year = int(m.group(1)) if m else None
        url = p.get("url", "")
        if url and not url.startswith("http"):
            url = f"https://www.nber.org{url}"
        results.append({
            "title": p.get("title", ""),
            "authors": authors,
            "year": year,
            "venue": "NBER Working Paper",
            "abstract": p.get("abstract", ""),
            "url": url,
            "doi": "",
            "full_text_url": "",
            "citations": None,
            "source": "nber",
        })
    return results


def _search_openalex(query: str, limit: int, year_start: int) -> list:
    import requests
    params = {
        "search": query,
        "filter": f"publication_year:>{year_start - 1}",
        "per-page": min(limit, 50),
        "select": "id,title,abstract_inverted_index,authorships,publication_year,primary_location,cited_by_count,doi,open_access",
        "sort": "cited_by_count:desc",
    }
    headers = {"User-Agent": "BID-IA-LiteratureReview/1.0 (fedesarrollo; mailto:research@fedesarrollo.org.co)"}
    r = requests.get("https://api.openalex.org/works", params=params, headers=headers, timeout=15)
    r.raise_for_status()
    results = []
    for p in r.json().get("results", []):
        if not p.get("title"):
            continue
        authors_list = p.get("authorships") or []
        authors = ", ".join(a.get("author", {}).get("display_name", "") for a in authors_list[:4])
        if len(authors_list) > 4:
            authors += " et al."
        inv = p.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            words = sorted([(pos, word) for word, positions in inv.items() for pos in positions])
            abstract = " ".join(w for _, w in words[:200])
        loc = p.get("primary_location") or {}
        venue = (loc.get("source") or {}).get("display_name", "")
        doi = p.get("doi", "")
        oa_url = (p.get("open_access") or {}).get("oa_url", "")
        url = oa_url or (f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else "")
        results.append({
            "title": p.get("title", ""),
            "authors": authors,
            "year": p.get("publication_year"),
            "venue": venue,
            "abstract": abstract,
            "url": url,
            "doi": doi,
            "full_text_url": oa_url,
            "citations": p.get("cited_by_count", 0),
            "source": "openalex",
        })
    return results


def _search_arxiv(query: str, limit: int, year_start: int) -> list:
    import requests
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    r = requests.get("http://export.arxiv.org/api/query", params=params, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
        summary_el = entry.find("atom:summary", ns)
        abstract = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""
        pub_el = entry.find("atom:published", ns)
        published = pub_el.text or "" if pub_el is not None else ""
        year = int(published[:4]) if published else None
        if year and year < year_start:
            continue
        authors_els = entry.findall("atom:author", ns)
        names = []
        for a in authors_els[:4]:
            n = a.find("atom:name", ns)
            names.append(n.text or "" if n is not None else "")
        authors = ", ".join(names)
        if len(authors_els) > 4:
            authors += " et al."
        id_el = entry.find("atom:id", ns)
        arxiv_id = (id_el.text or "").replace("http://arxiv.org/abs/", "").strip() if id_el is not None else ""
        results.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "arXiv",
            "abstract": abstract,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
            "doi": "",
            "full_text_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "citations": None,
            "source": "arxiv",
        })
    return results


def _search_ssrn(query: str, limit: int) -> list:
    """SSRN via Elsevier API. Requires SSRN_API_KEY in config or env."""
    import requests
    key = _cfg_key("ssrn_api_key")
    if not key:
        log.warning("[ssrn] SSRN_API_KEY not set — skipping")
        return []
    params = {"query": query, "count": min(limit, 50), "sort": "score"}
    headers = {"X-ELS-APIKey": key, "Accept": "application/json"}
    r = requests.get("https://api.ssrn.com/content/latest/search", params=params,
                     headers=headers, timeout=15)
    r.raise_for_status()
    results = []
    for p in r.json().get("results", []):
        title = p.get("title", "")
        if not title:
            continue
        authors_list = p.get("authors") or []
        authors = ", ".join(a.get("name", "") for a in authors_list[:4])
        if len(authors_list) > 4:
            authors += " et al."
        date_str = p.get("date", "")
        m = re.search(r"(\d{4})", date_str)
        year = int(m.group(1)) if m else None
        results.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "SSRN",
            "abstract": p.get("abstract", ""),
            "url": p.get("abstractLink", ""),
            "doi": p.get("doi", ""),
            "full_text_url": "",
            "citations": None,
            "source": "ssrn",
        })
    return results


_HEALTH_KEYWORDS = {
    "health", "wellbeing", "well-being", "mental", "burnout", "stress",
    "welfare", "illness", "sick", "medical", "clinical", "hospital",
    "worker health", "occupational", "safety", "fatigue",
}


def _pocket_has_health_keywords(pocket: str) -> bool:
    keywords = POCKETS.get(pocket, {}).get("keywords", [])
    kw_lower = {k.lower() for k in keywords}
    return bool(kw_lower & _HEALTH_KEYWORDS)


def _search_pubmed(query: str, limit: int) -> list:
    """PubMed NCBI E-utilities. Only called when pocket has health/wellbeing keywords."""
    import requests
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    api_key = _cfg_key("ncbi_api_key")
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(limit, 50),
        "retmode": "json",
        "sort": "relevance",
    }
    if api_key:
        search_params["api_key"] = api_key
    r = requests.get(f"{base}esearch.fcgi", params=search_params, timeout=15)
    r.raise_for_status()
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    if api_key:
        fetch_params["api_key"] = api_key
    r2 = requests.get(f"{base}efetch.fcgi", params=fetch_params, timeout=20)
    r2.raise_for_status()
    root = ET.fromstring(r2.content)
    results = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find(".//MedlineCitation")
        if medline is None:
            continue
        title_el = medline.find(".//ArticleTitle")
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue
        abstract_el = medline.find(".//AbstractText")
        abstract = (abstract_el.text or "").strip() if abstract_el is not None else ""
        year_el = medline.find(".//PubDate/Year")
        year = int(year_el.text) if year_el is not None and year_el.text else None
        journal_el = medline.find(".//Journal/Title")
        venue = (journal_el.text or "").strip() if journal_el is not None else ""
        author_els = medline.findall(".//Author")
        names = []
        for a in author_els[:4]:
            last = a.find("LastName")
            fore = a.find("ForeName")
            if last is not None:
                names.append(f"{fore.text + ' ' if fore is not None else ''}{last.text}")
        authors = ", ".join(names)
        if len(author_els) > 4:
            authors += " et al."
        pmid_el = medline.find("PMID")
        pmid = pmid_el.text if pmid_el is not None else ""
        doi = ""
        for id_el in article.findall(".//ArticleId"):
            if id_el.get("IdType") == "doi":
                doi = id_el.text or ""
        results.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "doi": doi,
            "full_text_url": f"https://doi.org/{doi}" if doi else "",
            "citations": None,
            "source": "pubmed",
        })
    return results


def _search_core(query: str, limit: int) -> list:
    """CORE: open access full text. Requires CORE_API_KEY."""
    import requests
    key = _cfg_key("core_api_key")
    if not key:
        log.warning("[core] CORE_API_KEY not set — skipping")
        return []
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    payload = {"q": query, "limit": min(limit, 50), "offset": 0}
    r = requests.post("https://api.core.ac.uk/v3/search/works", json=payload,
                      headers=headers, timeout=20)
    r.raise_for_status()
    results = []
    for p in r.json().get("results", []):
        title = p.get("title", "")
        if not title:
            continue
        authors_list = p.get("authors") or []
        authors = ", ".join(a.get("name", "") for a in authors_list[:4])
        if len(authors_list) > 4:
            authors += " et al."
        year = p.get("yearPublished")
        doi = p.get("doi", "")
        full_text = p.get("fullTextLink", "") or p.get("downloadUrl", "")
        results.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": p.get("publisher", ""),
            "abstract": p.get("abstract", ""),
            "url": full_text or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi,
            "full_text_url": full_text,
            "citations": p.get("citationCount"),
            "source": "core",
        })
    return results


def _search_worldbank(query: str, limit: int) -> list:
    """World Bank Open Knowledge Repository. No API key required."""
    import requests
    params = {
        "qterm": query,
        "docty": "Working Paper",
        "lang_exact": "English",
        "rows": min(limit, 50),
        "os": 0,
        "format": "json",
    }
    headers = {"User-Agent": "BID-IA-LiteratureReview/1.0"}
    r = requests.get("https://search.worldbank.org/api/v2/wds", params=params,
                     headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    docs = data.get("documents", {})
    results = []
    for doc_id, p in docs.items():
        if doc_id in ("facets", "total", "rows", "start"):
            continue
        title = p.get("display_title") or p.get("docdt", "")
        if not title:
            continue
        m = re.search(r"(\d{4})", str(p.get("docdt") or ""))
        year = int(m.group(1)) if m else None
        authors = p.get("authr", "")
        if isinstance(authors, list):
            authors = ", ".join(authors[:4])
        doi = p.get("doi", "")
        url = p.get("url", "") or (f"https://doi.org/{doi}" if doi else "")
        results.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "World Bank Working Paper",
            "abstract": p.get("abstract", ""),
            "url": url,
            "doi": doi,
            "full_text_url": p.get("pdfurl", ""),
            "citations": None,
            "source": "worldbank",
        })
    return results


def _search_imf(query: str, limit: int) -> list:
    """IMF eLibrary Working Papers. Requires IMF_API_KEY."""
    import requests
    key = _cfg_key("imf_api_key")
    if not key:
        log.warning("[imf] IMF_API_KEY not set — skipping")
        return []
    params = {
        "apikey": key,
        "query": query,
        "type": "Working Paper",
        "rows": min(limit, 50),
        "format": "json",
    }
    r = requests.get("https://www.elibrary.imf.org/api/search", params=params, timeout=15)
    r.raise_for_status()
    results = []
    for p in r.json().get("results", []):
        title = p.get("title", "")
        if not title:
            continue
        m = re.search(r"(\d{4})", str(p.get("date") or ""))
        year = int(m.group(1)) if m else None
        doi = p.get("doi", "")
        results.append({
            "title": title,
            "authors": p.get("authors", ""),
            "year": year,
            "venue": "IMF Working Paper",
            "abstract": p.get("abstract", ""),
            "url": p.get("url", "") or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi,
            "full_text_url": "",
            "citations": None,
            "source": "imf",
        })
    return results


# ── Corpus helpers ─────────────────────────────────────────────────────────────

def _paper_classification(p: dict) -> str:
    """Read classification from either new schema (agent_classification) or old (status)."""
    cl = p.get("agent_classification") or p.get("status", "")
    # normalise legacy Spanish labels
    return {"ACEPTADO": "ACCEPTED", "REVISAR": "REVIEW", "RECHAZADO": "REJECTED"}.get(cl, cl)


def get_corpus_status() -> dict:
    status = {}
    total_accepted = total_papers = 0
    for pocket in POCKETS:
        for fname in [f"data/{pocket}_reviewed_enriched.json",
                      f"data/{pocket}_reviewed.json",
                      f"data/{pocket}_papers_enriched.json"]:
            f = ROOT / fname
            if f.exists():
                papers = json.loads(f.read_text())
                accepted  = sum(1 for p in papers if _paper_classification(p) == "ACCEPTED")
                review    = sum(1 for p in papers if _paper_classification(p) == "REVIEW")
                rejected  = sum(1 for p in papers if _paper_classification(p) == "REJECTED")
                human_val = sum(1 for p in papers if p.get("human_classification"))
                sources   = {p.get("source", "unknown") for p in papers}
                status[pocket] = {
                    "total": len(papers),
                    "accepted": accepted,
                    "review": review,
                    "rejected": rejected,
                    "human_validated": human_val,
                    "non_rejected": accepted + review,
                    "with_abstract": sum(1 for p in papers if p.get("abstract")),
                    "sources": list(sources),
                    "source_file": f.name,
                }
                total_accepted += accepted
                total_papers += len(papers)
                break
        else:
            status[pocket] = {"total": 0, "note": "no data file found"}
    status["_summary"] = {
        "total_papers": total_papers,
        "total_accepted": total_accepted,
        "goal": 420,
        "pct_goal": round(total_accepted / 420 * 100, 1),
    }
    return status


def load_papers(pocket: str, status_filter: str = None) -> list:
    """Load papers from a pocket file. status_filter accepts new-schema (ACCEPTED/REVIEW/REJECTED)
    or legacy Spanish labels (ACEPTADO/REVISAR/RECHAZADO)."""
    # Normalise filter to new schema
    _legacy = {"ACEPTADO": "ACCEPTED", "REVISAR": "REVIEW", "RECHAZADO": "REJECTED"}
    if status_filter in _legacy:
        status_filter = _legacy[status_filter]
    for fname in [f"data/{pocket}_reviewed_enriched.json",
                  f"data/{pocket}_reviewed.json",
                  f"data/{pocket}_papers_enriched.json"]:
        f = ROOT / fname
        if f.exists():
            papers = json.loads(f.read_text())
            if status_filter:
                papers = [p for p in papers if _paper_classification(p) == status_filter]
            return papers[:100]
    return []


def save_papers(pocket: str, papers: list, mode: str = "merge") -> dict:
    out_path = ROOT / f"data/{pocket}_reviewed_enriched.json"
    if mode == "merge" and out_path.exists():
        existing = json.loads(out_path.read_text())
        existing_keys = {p.get("title", "").lower()[:60] for p in existing}
        added = 0
        for p in papers:
            key = p.get("title", "").lower()[:60]
            if key and key not in existing_keys:
                existing.append(p)
                existing_keys.add(key)
                added += 1
        out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
        return {"saved": added, "total": len(existing), "file": str(out_path)}
    else:
        out_path.write_text(json.dumps(papers, ensure_ascii=False, indent=2))
        return {"saved": len(papers), "total": len(papers), "file": str(out_path)}


# ── Crossref enrichment ───────────────────────────────────────────────────────

def _enrich_with_crossref(papers: list) -> list:
    """Query Crossref for each paper that has a DOI. Adds journal, ISSN, formal cites, ORCID."""
    import requests
    headers = {
        "User-Agent": "BID-IA-LiteratureReview/1.0 (mailto:m.montoyac@uniandes.edu.co)"
    }
    enriched = []
    for p in papers:
        doi = p.get("doi", "").strip()
        # Normalise DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        if not doi:
            enriched.append(p)
            continue
        try:
            r = requests.get(f"https://api.crossref.org/works/{doi}", headers=headers, timeout=10)
            if r.status_code != 200:
                enriched.append(p)
                continue
            msg = r.json().get("message", {})
            # Journal name and ISSN
            container = msg.get("container-title", [])
            journal = container[0] if container else ""
            issn_list = msg.get("ISSN", [])
            issn = issn_list[0] if issn_list else ""
            # Citation count
            cite_count = msg.get("is-referenced-by-count")
            # Formal publication date
            published = msg.get("published", {}).get("date-parts", [[None]])
            formal_year = published[0][0] if published and published[0] else None
            # Authors with ORCID
            cr_authors = msg.get("author", [])
            def _fmt_author(a):
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                orcid = a.get("ORCID", "").replace("http://orcid.org/", "")
                return f"{name} [{orcid}]" if orcid else name
            normalized_authors = ", ".join(_fmt_author(a) for a in cr_authors[:4])
            if len(cr_authors) > 4:
                normalized_authors += " et al."
            p = {
                **p,
                "doi": doi,
                "journal": journal or p.get("venue", ""),
                "issn": issn,
                "citations": cite_count if cite_count is not None else p.get("citations"),
                "formal_year": formal_year,
                "authors_normalized": normalized_authors or p.get("authors", ""),
            }
        except Exception as e:
            log.warning(f"[crossref] DOI {doi}: {e}")
        enriched.append(p)
        time.sleep(0.1)  # polite — Crossref allows ~50 req/s politely
    return enriched


# ── Deduplication ─────────────────────────────────────────────────────────────

def _title_key(title: str) -> str:
    _STOPWORDS = {"the", "a", "an", "of", "in", "on", "and", "for", "to", "with",
                  "is", "are", "do", "does", "evidence", "from", "using"}
    words = re.sub(r"[^a-z0-9 ]", "", title.lower()).split()
    return " ".join(w for w in words if w not in _STOPWORDS)


def _title_similar(a: str, b: str) -> bool:
    ratio = difflib.SequenceMatcher(None, _title_key(a), _title_key(b)).ratio()
    return (1 - ratio) < 0.15  # distance < 0.15


def _deduplicate(papers: list) -> tuple[list, dict]:
    """Deduplicate by DOI > title similarity > (first_author, year).
    Returns (deduped_list, log_dict)."""
    seen_doi: dict[str, int] = {}      # doi → index in kept
    kept: list[dict] = []
    dup_log: dict[str, int] = {}       # "sourceA↔sourceB" → count

    def _dup_key(p1, p2):
        s1 = p1.get("source", "?")
        s2 = p2.get("source", "?")
        return f"{min(s1,s2)}↔{max(s1,s2)}"

    for paper in papers:
        doi = (paper.get("doi") or "").strip().lower()
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        # 1. DOI exact match
        if doi:
            if doi in seen_doi:
                key = _dup_key(paper, kept[seen_doi[doi]])
                dup_log[key] = dup_log.get(key, 0) + 1
                continue
            seen_doi[doi] = len(kept)
            kept.append(paper)
            continue

        # 2. Title similarity
        title = paper.get("title", "")
        matched = False
        for i, existing in enumerate(kept):
            if _title_similar(title, existing.get("title", "")):
                key = _dup_key(paper, existing)
                dup_log[key] = dup_log.get(key, 0) + 1
                matched = True
                break
        if matched:
            continue

        # 3. (first author last name, year) fallback
        first_author = re.split(r"[,\s]", paper.get("authors", ""))[0].lower()
        year = paper.get("year")
        if first_author and year:
            author_year_key = f"{first_author}_{year}"
            for existing in kept:
                ea = re.split(r"[,\s]", existing.get("authors", ""))[0].lower()
                if ea == first_author and existing.get("year") == year:
                    key = _dup_key(paper, existing)
                    dup_log[key] = dup_log.get(key, 0) + 1
                    matched = True
                    break
            if matched:
                continue

        kept.append(paper)

    return kept, dup_log


# ── Coverage evaluation ───────────────────────────────────────────────────────

def _evaluate_coverage(papers: list, pocket: str) -> dict:
    """Returns a 0–1 coverage score with diagnostics.
    Target: 60 ACCEPTED+REVIEW papers per pocket (Change 4)."""
    target = CONFIG.get("coverage_target", 60)  # CHANGE 4: was 20
    if not papers:
        return {"score": 0.0, "reason": "no papers", "details": {}}

    # Count only non-rejected papers (ACCEPTED + REVIEW)
    non_rejected = [p for p in papers if _paper_classification(p) != "REJECTED"]
    effective_count = len(non_rejected)

    # Criterion 1: quantity (0–0.4) — based on non-rejected count vs target
    quantity_score = min(effective_count / target, 1.0) * 0.4

    # Criterion 2: temporal diversity (0–0.3) — penalise if all same year
    years = [p.get("year") for p in papers if p.get("year")]
    if len(set(years)) >= 4:
        temporal_score = 0.3
    elif len(set(years)) >= 2:
        temporal_score = 0.15
    else:
        temporal_score = 0.0

    # Criterion 3: source diversity (0–0.2) — bonus for 3+ distinct sources
    sources = {p.get("source", "") for p in papers}
    if len(sources) >= 3:
        source_score = 0.2
    elif len(sources) >= 2:
        source_score = 0.1
    else:
        source_score = 0.0

    # Criterion 4: full text availability (0–0.1)
    with_full_text = sum(1 for p in papers if p.get("full_text_url"))
    fulltext_score = min(with_full_text / max(len(papers), 1), 1.0) * 0.1

    score = round(quantity_score + temporal_score + source_score + fulltext_score, 3)
    return {
        "score": score,
        "threshold": 0.6,
        "needs_more": score < 0.6,
        "details": {
            "papers_total": len(papers),
            "papers_non_rejected": effective_count,  # ACCEPTED + REVIEW
            "target": target,
            "quantity_score": round(quantity_score, 3),
            "years_covered": sorted(set(years)),
            "temporal_score": round(temporal_score, 3),
            "sources": sorted(sources),
            "source_score": round(source_score, 3),
            "with_full_text": with_full_text,
            "fulltext_score": round(fulltext_score, 3),
        },
        "recommendation": (
            f"Coverage sufficient — {effective_count}/{target} non-rejected papers."
            if score >= 0.6
            else f"Score {score} < 0.6. Need {target - effective_count} more ACCEPTED/REVIEW papers. Try alternative queries."
        ),
    }


# ── Tool definitions for Claude ──────────────────────────────────────────────

_ALL_SOURCES = [
    "semantic_scholar", "nber", "openalex", "arxiv",
    "ssrn", "pubmed", "core", "worldbank", "imf",
]

TOOLS = [
    {
        "name": "get_corpus_status",
        "description": (
            "Returns current state of the literature corpus: papers per pocket, "
            "accepted/revisar/rejected counts, abstract coverage, and progress toward goal. "
            "Always call this first to understand what exists and what's missing."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_pocket_definition",
        "description": (
            "Returns the full definition of a pocket: central research question, "
            "why it matters for the Guatiguara RCT, the 8 curated search queries, anchor papers, "
            "quality signals, and 5 acceptance criteria. Always call before searching or reviewing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pocket": {"type": "string", "enum": list(POCKETS.keys())}
            },
            "required": ["pocket"],
        },
    },
    {
        "name": "search_papers",
        "description": (
            "Search for academic papers. Nine sources available:\n"
            "- 'semantic_scholar': broad coverage (ArXiv + journals + WPs). Good for CS/interdisciplinary.\n"
            "- 'nber': NBER working papers. Best for economics.\n"
            "- 'openalex': 240M works, free, best citation counts.\n"
            "- 'arxiv': CS/AI preprints 2024-2026. Best for very recent LLM papers.\n"
            "- 'ssrn': economics/finance/social science preprints. Requires SSRN_API_KEY.\n"
            "- 'pubmed': biomedical. Only for pockets with health/wellbeing keywords.\n"
            "- 'core': open access full text fallback. Requires CORE_API_KEY.\n"
            "- 'worldbank': World Bank working papers. Good for development/labor pockets.\n"
            "- 'imf': IMF working papers. Good for macro/finance pockets. Requires IMF_API_KEY.\n\n"
            "Results are cached 24h by default. Use the pocket's curated queries as starting point."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "source": {"type": "string", "enum": _ALL_SOURCES, "default": "semantic_scholar"},
                "limit": {"type": "integer", "default": 20},
                "year_start": {"type": "integer", "default": 2020},
                "pocket": {
                    "type": "string",
                    "enum": list(POCKETS.keys()),
                    "description": "Current pocket — used for cache keying and PubMed gating.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "enrich_metadata",
        "description": (
            "Enrich a list of papers via the Crossref API using their DOIs. "
            "Adds: canonical DOI, journal name, ISSN, formal citation count, "
            "publication date, and author ORCID. Papers without a DOI are returned unchanged. "
            "Call this after search_papers and before review_papers_with_ai."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["papers"],
        },
    },
    {
        "name": "deduplicate_papers",
        "description": (
            "Remove duplicate papers from a combined list. Priority: "
            "1) exact DOI match, 2) title similarity (Levenshtein < 0.15), "
            "3) first-author + year. Returns the deduplicated list and a log of "
            "duplicate counts per source pair (e.g., 'arxiv<->ssrn: 3'). "
            "Call after enrich_metadata and before review_papers_with_ai."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["papers"],
        },
    },
    {
        "name": "evaluate_corpus_coverage",
        "description": (
            "Analyse the current paper list and return a coverage score 0-1. "
            "Considers: quantity vs target, temporal diversity, source diversity, "
            "and full-text availability. If score < 0.6, search more before reviewing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {"type": "array", "items": {"type": "object"}},
                "pocket": {"type": "string", "enum": list(POCKETS.keys())},
            },
            "required": ["papers", "pocket"],
        },
    },
    {
        "name": "review_papers_with_ai",
        "description": (
            # CHANGE 1+2+7: replaced rubric-based scoring with anchor-paper signal classification.
            # Uses Sonnet (not Haiku). Suggests ACCEPTED/REVIEW/REJECTED — human reviews.
            "Classify papers against the pocket using anchor papers as the quality/relevance bar. "
            "Suggests ACCEPTED (clearly matches anchor papers in topic/methodology/question), "
            "REVIEW (ambiguous — needs human judgment), or REJECTED (clearly not relevant). "
            "This is an AGENT SUGGESTION ONLY — human reviews all classifications. "
            "Pass anchor_papers (external JSON list) to supplement pocket's built-in anchor papers. "
            "Pass iteration number to track which run found each paper."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {"type": "array", "items": {"type": "object"}},
                "pocket": {"type": "string", "enum": list(POCKETS.keys())},
                "pocket_definition": {
                    "type": "object",
                    "description": "Result from get_pocket_definition — provides pocket context.",
                },
                "anchor_papers": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "External anchor papers (id, title, authors, year, journal, abstract, quality).",
                },
                "iteration": {
                    "type": "integer",
                    "description": "Current iteration number (0-indexed). Stored on each paper.",
                    "default": 0,
                },
            },
            "required": ["papers", "pocket"],
        },
    },
    {
        "name": "cluster_papers",
        "description": (
            # CHANGE 5: new tool — groups ACCEPTED papers into thematic clusters.
            "Group ACCEPTED papers into 3-8 thematic clusters to help a human read 60 papers "
            "strategically. For each cluster: short descriptive label, list of paper IDs, "
            "2-3 recommended first-reads, and rationale for that recommendation. "
            "Output is a separate JSON file (pocket_clusters.json). "
            "Call this after classification, passing only ACCEPTED papers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {"type": "array", "items": {"type": "object"}},
                "pocket": {"type": "string", "enum": list(POCKETS.keys())},
            },
            "required": ["papers", "pocket"],
        },
    },
    {
        "name": "load_papers",
        "description": "Load existing papers from a pocket's data file, optionally filtered by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pocket": {"type": "string", "enum": list(POCKETS.keys())},
                "status_filter": {
                    "type": "string",
                    "enum": ["ACEPTADO", "REVISAR", "RECHAZADO"],
                },
            },
            "required": ["pocket"],
        },
    },
    {
        "name": "save_papers",
        "description": (
            "Save reviewed papers to a pocket's data file. "
            "mode='merge' adds new papers without overwriting existing ones (default). "
            "mode='overwrite' replaces the file entirely."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pocket": {"type": "string", "enum": list(POCKETS.keys())},
                "papers": {"type": "array", "items": {"type": "object"}},
                "mode": {"type": "string", "enum": ["merge", "overwrite"], "default": "merge"},
            },
            "required": ["pocket", "papers"],
        },
    },
]


# ── Tool executor ─────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict, client: anthropic.Anthropic) -> str:

    if name == "get_corpus_status":
        return json.dumps(get_corpus_status(), ensure_ascii=False, indent=2)

    if name == "get_pocket_definition":
        pocket = inputs["pocket"]
        p = POCKETS[pocket]
        return json.dumps({
            "pocket": pocket,
            "label": p["label"],
            "priority": p["priority"],
            "central_question": p["question"],
            "why_it_matters": p["why"],
            "anchor_papers": p["anchor_papers"],
            "curated_queries": p["queries"],
            "quality_signals": p["quality_signals"],
            "acceptance_criteria": p["accept_criteria"],
            "keywords": p["keywords"],
            "rubric": RUBRIC,
        }, ensure_ascii=False, indent=2)

    if name == "search_papers":
        source = inputs.get("source", "semantic_scholar")
        query = inputs["query"]
        limit = inputs.get("limit", 20)
        year_start = inputs.get("year_start", 2020)
        pocket = inputs.get("pocket", "")
        time.sleep(0.5)

        # PubMed gate: only run if pocket has health keywords
        if source == "pubmed" and pocket and not _pocket_has_health_keywords(pocket):
            return json.dumps({"skipped": True, "reason": "pocket has no health/wellbeing keywords"})

        # Cache check
        ck = _cache_key(pocket, source, query, {"limit": limit, "year_start": year_start})
        cached = _cache_get(ck)
        if cached is not None:
            log.info(f"cache hit: {source}")
            return json.dumps(cached, ensure_ascii=False)

        source_fns = {
            "semantic_scholar": lambda: _search_semantic_scholar(query, limit, year_start),
            "nber": lambda: _search_nber(query, limit),
            "openalex": lambda: _search_openalex(query, limit, year_start),
            "arxiv": lambda: _search_arxiv(query, limit, year_start),
            "ssrn": lambda: _search_ssrn(query, limit),
            "pubmed": lambda: _search_pubmed(query, limit),
            "core": lambda: _search_core(query, limit),
            "worldbank": lambda: _search_worldbank(query, limit),
            "imf": lambda: _search_imf(query, limit),
        }
        fn = source_fns.get(source)
        if not fn:
            return json.dumps({"error": f"Unknown source: {source}"})

        result = safe_execute_tool(fn, tool_name=source)
        if isinstance(result, list) and result and "error" not in result[0]:
            _cache_set(ck, result)
        return json.dumps(result, ensure_ascii=False)

    if name == "enrich_metadata":
        papers = inputs["papers"]
        result = safe_execute_tool(_enrich_with_crossref, papers, tool_name="crossref")
        return json.dumps(result, ensure_ascii=False)

    if name == "deduplicate_papers":
        papers = inputs["papers"]
        deduped, dup_log = _deduplicate(papers)
        total_dups = sum(dup_log.values())
        return json.dumps({
            "papers": deduped,
            "original_count": len(papers),
            "deduped_count": len(deduped),
            "duplicates_removed": total_dups,
            "by_source_pair": dup_log,
        }, ensure_ascii=False)

    if name == "evaluate_corpus_coverage":
        result = _evaluate_coverage(inputs["papers"], inputs["pocket"])
        return json.dumps(result, ensure_ascii=False)

    if name == "load_papers":
        return json.dumps(load_papers(inputs["pocket"], inputs.get("status_filter")), ensure_ascii=False)

    if name == "save_papers":
        return json.dumps(save_papers(inputs["pocket"], inputs["papers"], inputs.get("mode", "merge")))

    if name == "review_papers_with_ai":
        # CHANGE 1+2+3+7+8: anchor-based classification, Sonnet, new schema, no rubric.
        pocket = inputs["pocket"]
        papers = inputs["papers"][:30]
        pdef = inputs.get("pocket_definition") or {}
        external_anchors = inputs.get("anchor_papers") or []  # CHANGE 2
        iteration = inputs.get("iteration", 0)                 # CHANGE 2
        p = POCKETS[pocket]

        # Build anchor papers list from pocket definition + any external anchors
        pocket_anchors = p.get("anchor_papers", [])
        external_anchor_lines = [
            f"{ap.get('title', '')} ({ap.get('year', '')}) — {', '.join(ap.get('authors', []))}"
            for ap in external_anchors
        ]
        all_anchors = pocket_anchors + external_anchor_lines
        anchors_text = "\n".join(f"  • {a}" for a in all_anchors)

        subquestions_text = "\n".join(
            f"  - {c}" for c in pdef.get("acceptance_criteria", p["accept_criteria"])
        )

        papers_text = "\n\n".join(
            f"PAPER {i+1}:\nTitle: {p2.get('title','')}\n"
            f"Authors: {p2.get('authors','')} | Year: {p2.get('year','')} | "
            f"Venue: {p2.get('venue','')}\n"
            f"Abstract: {(p2.get('abstract') or 'NO ABSTRACT')[:600]}"
            for i, p2 in enumerate(papers)
        )

        # CHANGE 8: tightened pocket prompt structure
        system = (
            "You are a research assistant helping with a literature review on the "
            "causal impact of AI adoption.\n\n"
            f"For this pocket, the central research question is: "
            f"{pdef.get('central_question', p['question'])}\n\n"
            f"Sub-questions guiding this pocket:\n{subquestions_text}\n\n"
            "Search scope: We are interested in AI adoption within private sector firms, "
            "at the worker or firm level. Do NOT classify as ACCEPTED papers that address "
            "AI adoption at the country or macro level unless they have a firm-level component.\n\n"
            f"Anchor papers (these define the quality and relevance bar):\n{anchors_text}"
        )

        prompt = f"""You have been given anchor papers that represent exactly what we are looking for.
A paper is ACCEPTED if it closely matches the topic, methodology, or research question of the anchor papers.
It is REJECTED if it clearly does not.
It is REVIEW if you are uncertain.

# HUMAN REVIEWS THIS — agent suggestion only

For each paper, return a JSON object with EXACTLY this structure:
{{
  "title": "<exact title as given>",
  "agent_classification": "<ACCEPTED|REVIEW|REJECTED>",
  "agent_classification_reason": "<one sentence explaining why, referencing anchor papers if relevant>"
}}

Return ONLY a JSON array, one object per paper. No preamble, no explanation.

PAPERS:
{papers_text}
"""
        # CHANGE 7: was claude-haiku-4-5-20251001
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start, end = raw.find("["), raw.rfind("]") + 1
        if start == -1 or end <= start:
            return json.dumps({"error": "Could not parse review", "raw": raw[:500]})
        reviews = json.loads(raw[start:end])
        review_map = {r["title"].lower()[:60]: r for r in reviews}

        # CHANGE 3: output uses new state schema
        reviewed = []
        for p2 in papers:
            key = p2.get("title", "").lower()[:60]
            rev = review_map.get(key)
            doi = (p2.get("doi") or "").strip().replace("https://doi.org/", "")
            paper_id = doi or p2.get("url", "") or f"unknown_{key[:20]}"
            new_paper = {
                "id": paper_id,
                "title": p2.get("title", ""),
                "authors": p2.get("authors", ""),
                "year": p2.get("year"),
                "journal": p2.get("venue", "") or p2.get("journal", ""),
                "abstract": p2.get("abstract", ""),
                "source": p2.get("source", ""),
                "pocket": pocket,
                "agent_classification": rev.get("agent_classification", "REVIEW") if rev else "REVIEW",
                # HUMAN REVIEWS THIS — agent suggestion only
                "agent_classification_reason": rev.get("agent_classification_reason", "") if rev else "",
                "human_classification": None,  # filled by human later
                "iteration_found": iteration,
                # preserve lookup fields
                "url": p2.get("url", ""),
                "doi": doi,
                "full_text_url": p2.get("full_text_url", ""),
                "citations": p2.get("citations"),
            }
            reviewed.append(new_paper)
        return json.dumps(reviewed, ensure_ascii=False)

    # CHANGE 5: new cluster_papers tool
    if name == "cluster_papers":
        pocket = inputs["pocket"]
        papers = inputs["papers"][:80]  # cluster up to 80 accepted papers

        papers_text = "\n\n".join(
            f"[{p2.get('id', p2.get('doi', f'p{i}'))}] {p2.get('title','')}\n"
            f"Abstract: {(p2.get('abstract') or '')[:400]}"
            for i, p2 in enumerate(papers)
        )

        prompt = f"""Given the following list of accepted papers (IDs + titles + abstracts),
identify between 3 and 8 thematic groups. For each group:
- Give it a short descriptive label (not a headline, a description of the theme)
- List the paper IDs that belong to it
- Recommend the 2-3 most representative papers to read first in that group
- Briefly explain what reading those 2-3 papers would cover

The goal is to help a human researcher read {len(papers)} papers strategically
by reading ~{min(len(papers)//3, 18)} representative ones first.

Return ONLY a JSON object with this structure:
{{
  "pocket": "{pocket}",
  "clusters": [
    {{
      "cluster_id": 1,
      "label": "<short descriptive label>",
      "paper_ids": ["<id1>", "<id2>", ...],
      "recommended_reads": ["<id1>", "<id2>", "<id3>"],
      "rationale": "<one sentence: what reading these covers>"
    }}
  ]
}}

No preamble, no explanation outside the JSON.

PAPERS:
{papers_text}
"""
        # CHANGE 7: Sonnet for clustering too
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            return json.dumps({"error": "Could not parse clusters", "raw": raw[:500]})
        clusters = json.loads(raw[start:end])

        # Save clusters to file
        out_path = ROOT / f"data/{pocket}_clusters.json"
        out_path.write_text(json.dumps(clusters, ensure_ascii=False, indent=2))
        clusters["saved_to"] = str(out_path)
        return json.dumps(clusters, ensure_ascii=False)

    # synthesize_papers REMOVED (Change 6) — we read papers ourselves

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are the BID-IA Literature Review Agent for Fedesarrollo & BID.

{PROJECT_CONTEXT}

HOW TO APPROACH TASKS:
1. Start with get_corpus_status — understand what exists, what's missing, what's below target (60 per pocket).
2. For any pocket, call get_pocket_definition first — it has the exact curated queries and anchor papers.
   Store the result and pass it as pocket_definition to review_papers_with_ai.
3. When searching: use the pocket's curated queries. Search 2-3 sources per round.
   Source strategy: NBER for economics (labor, desigualdad, evaluacion_experimental);
   ArXiv for recent CS/AI papers; OpenAlex for citation counts; Semantic Scholar for breadth;
   SSRN for economics/finance preprints; World Bank for development/labor; IMF for macro.
4. After each round of search_papers, call evaluate_corpus_coverage.
   Target: 60 ACCEPTED+REVIEW papers per pocket. If score < 0.6, search more before reviewing.
5. After collecting from multiple sources, call enrich_metadata then deduplicate_papers.
6. Classification: call review_papers_with_ai. This suggests ACCEPTED/REVIEW/REJECTED based on
   anchor papers as the relevance bar. DO NOT use numeric scores. The human reviews all suggestions.
7. After classification, call cluster_papers on ACCEPTED papers only.
8. Always save_papers before ending the task.
9. DO NOT call synthesize_papers — it has been removed. We read papers ourselves.

OUTPUTS PER RUN (three files only):
- {"{pocket}"}_reviewed_enriched.json — classified papers (agent_classification + human_classification)
- {"{pocket}"}_clusters.json — thematic clusters of ACCEPTED papers
- run report: total_found, accepted, review, rejected, duplicates_removed

ERROR HANDLING:
- If a tool returns {{"error": true}}, log the source and continue with available data.
- List any sources that failed: "SSRN unavailable (no API key). Searched 4/5 sources."

COMMUNICATION: Be concise.
After search: "Found N papers from [source]."
After classification: "Classified N: X ACCEPTED, Y REVIEW, Z REJECTED."
After clusters: "Created N clusters. Recommended reads: [titles]."
"""


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_agent(task: str, api_key: str, verbose: bool = False):
    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": task}]

    print(f"\n{'─'*60}")
    print(f"TASK: {task}")
    print(f"{'─'*60}\n")

    max_iterations = 30
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        if iteration > 1:
            time.sleep(12)  # avoid 30k token/min rate limit
        for _attempt in range(4):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
                break
            except anthropic.RateLimitError as e:
                wait = 30 * (2 ** _attempt)
                log.warning(f"Anthropic rate limit — waiting {wait}s (attempt {_attempt+1}/4): {e}")
                if _attempt == 3:
                    raise
                time.sleep(wait)
        else:
            raise RuntimeError("Exhausted retries on Anthropic rate limit")

        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(block.text)

        if response.stop_reason == "end_turn":
            break

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            print(f"\n⚙️  [{tu.name}] {json.dumps(tu.input)[:100]}...")
            result = execute_tool(tu.name, tu.input, client)
            if verbose:
                print(f"   → {result[:400]}")
            else:
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        if parsed and isinstance(parsed[0], dict) and parsed[0].get("error"):
                            print(f"   ❌ {parsed[0].get('reason', parsed[0])}")
                        else:
                            print(f"   → {len(parsed)} items")
                    elif isinstance(parsed, dict) and "_summary" in parsed:
                        s = parsed["_summary"]
                        print(f"   → {s['total_accepted']}/{s['goal']} accepted ({s['pct_goal']}%)")
                    elif isinstance(parsed, dict) and "deduped_count" in parsed:
                        print(f"   → {parsed['deduped_count']} unique ({parsed['duplicates_removed']} dups removed)")
                    elif isinstance(parsed, dict) and "score" in parsed and "threshold" in parsed:
                        print(f"   → coverage score: {parsed['score']} ({'ok' if not parsed['needs_more'] else 'needs more'})")
                    elif isinstance(parsed, dict):
                        print(f"   → {json.dumps(parsed)[:150]}")
                except Exception:
                    print(f"   → {result[:150]}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    if iteration >= max_iterations:
        print(f"\n⚠️  Reached max_iterations={max_iterations}. Stopping.")

    print(f"\n{'─'*60}\nDone.\n")


# ── Human-in-the-loop iteration cycle (Change 9) ─────────────────────────────

def _count_state(pocket: str) -> dict:
    """Count papers in current state file by classification."""
    papers = load_papers(pocket)
    return {
        "accepted":  sum(1 for p in papers if _paper_classification(p) == "ACCEPTED"),
        "review":    sum(1 for p in papers if _paper_classification(p) == "REVIEW"),
        "rejected":  sum(1 for p in papers if _paper_classification(p) == "REJECTED"),
        "total":     len(papers),
        "titles":    {p.get("title", "").lower()[:60] for p in papers},
    }


def run_pocket_iteration(
    pocket: str,
    api_key: str,
    anchor_papers: list = None,
    verbose: bool = False,
    max_outer_iterations: int = 7,
):
    """Human-in-the-loop iteration cycle for a single pocket.

    Cycle per iteration:
      1. Agent searches and suggests classifications (ACCEPTED/REVIEW/REJECTED)
      2. Human reviews suggestions (reads abstracts/intros) and edits human_classification
      3. Agent reads human-validated state as refined signal for next search
      4. Repeat until stopping condition

    Stopping conditions:
      - No new papers found in last iteration, OR
      - max_outer_iterations (hard cap, default 7) reached

    CLI usage:
      python scripts/agent.py --pocket labor --iterate
      python scripts/agent.py --pocket labor --iterate --anchor-papers anchors.json
    """
    anchor_papers = anchor_papers or []
    client = anthropic.Anthropic(api_key=api_key)

    for outer_iter in range(max_outer_iterations):
        state_before = _count_state(pocket)

        # ── Iteration start log ────────────────────────────────────────────
        print(f"\n{'═'*60}")
        print(
            f"Starting iteration {outer_iter}. "
            f"Papers in state: {state_before['accepted']} accepted, "
            f"{state_before['review']} review, {state_before['rejected']} rejected. "
            f"New papers found last iteration: "
            f"{'N/A (first run)' if outer_iter == 0 else str(state_before['total'] - _prev_total)}. "
            f"Stopping if 0 new papers found."
        )
        print(f"{'═'*60}\n")

        # Build task string with iteration context
        if outer_iter == 0:
            signal = "Use the pocket's anchor papers as the sole relevance signal."
        else:
            n_accepted = state_before["accepted"]
            signal = (
                f"This is iteration {outer_iter}. "
                f"There are already {n_accepted} ACCEPTED papers (human-validated) in state. "
                "Load them with load_papers(status_filter='ACCEPTED') and use them as "
                "additional relevance signal alongside the anchor papers. "
                "Search for papers SIMILAR to these accepted ones that are NOT yet in state."
            )

        anchor_json = json.dumps(anchor_papers) if anchor_papers else "[]"
        task = (
            f"Run iteration {outer_iter} of the literature search for pocket '{pocket}'.\n\n"
            f"{signal}\n\n"
            f"External anchor papers (JSON): {anchor_json}\n\n"
            "Steps:\n"
            "1. get_corpus_status\n"
            "2. get_pocket_definition\n"
            "3. Search 2-3 sources using curated queries\n"
            "4. enrich_metadata then deduplicate_papers (skip papers already in state)\n"
            "5. evaluate_corpus_coverage — target 60 ACCEPTED+REVIEW. If < 0.6, search more\n"
            f"6. review_papers_with_ai with iteration={outer_iter} and the external anchor_papers\n"
            "7. cluster_papers on ACCEPTED papers\n"
            "8. save_papers (merge mode)\n"
            "9. Report: total found, accepted, review, rejected, duplicates removed"
        )

        run_agent(task, api_key, verbose)

        state_after = _count_state(pocket)
        _prev_total = state_after["total"]
        new_papers = state_after["total"] - state_before["total"]

        # ── Iteration end log ──────────────────────────────────────────────
        print(f"\n{'─'*60}")
        print(
            f"Iteration {outer_iter} complete. New papers added: {new_papers}. "
            f"Run again? Waiting for human classification before next iteration."
        )
        print(f"{'─'*60}")

        # ── Stopping condition 1: no new papers ───────────────────────────
        if outer_iter > 0 and new_papers == 0:
            print("\nStopping condition met: no new papers found. Pipeline complete.")
            break

        # ── Stopping condition 2: coverage reached ────────────────────────
        non_rejected = state_after["accepted"] + state_after["review"]
        if non_rejected >= 60:
            print(f"\nStopping condition met: {non_rejected} ACCEPTED+REVIEW papers (target: 60).")
            break

        # ── Human-in-the-loop pause ────────────────────────────────────────
        if outer_iter < max_outer_iterations - 1:
            print(
                f"\nNext: review agent suggestions in data/{pocket}_reviewed_enriched.json\n"
                "  Set human_classification = 'ACCEPTED' | 'REVIEW' | 'REJECTED' for each paper.\n"
                "  Then press ENTER to run next iteration, or type 'stop' to exit."
            )
            try:
                user_input = input("Human classification complete? ").strip().lower()
                if user_input == "stop":
                    print("Exiting iteration loop.")
                    break
            except (KeyboardInterrupt, EOFError):
                print("\nInterrupted. Exiting.")
                break
    else:
        print(f"\nReached max_outer_iterations={max_outer_iterations}. Stopping.")

    # Final run report
    final = _count_state(pocket)
    report = {
        "pocket": pocket,
        "iteration": outer_iter,
        "total_found": final["total"],
        "accepted": final["accepted"],
        "review": final["review"],
        "rejected": final["rejected"],
        "duplicates_removed": 0,  # tracked per-run above
    }
    print(f"\nFinal report: {json.dumps(report, indent=2)}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BID-IA Literature Review Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python scripts/agent.py --status
          python scripts/agent.py --pocket labor
          python scripts/agent.py --pocket evaluacion_experimental --mode search
          python scripts/agent.py "what gaps exist in our current corpus?"
          python scripts/agent.py "find papers by Brynjolfsson and Autor about AI wages"
          python scripts/agent.py --interactive
        """),
    )
    parser.add_argument("task", nargs="?")
    parser.add_argument("--pocket", choices=list(POCKETS.keys()))
    parser.add_argument("--mode", choices=["search", "review", "full"], default="full",
                        help="search=find papers only; review=classify existing; full=end-to-end")
    parser.add_argument("--iterate", action="store_true",
                        help="Run human-in-the-loop iteration cycle (Change 9). "
                             "Pauses between iterations for human classification.")
    parser.add_argument("--anchor-papers",
                        help="Path to JSON file with external anchor papers "
                             "[{id, title, authors, year, journal, abstract, quality}]")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--api-key")
    args = parser.parse_args()

    if args.status:
        status = get_corpus_status()
        summary = status.pop("_summary")
        print(f"\n{'─'*50}")
        print(f"BID-IA Corpus  |  Goal: {summary['goal']} papers")
        print(f"Accepted: {summary['total_accepted']} / {summary['goal']} ({summary['pct_goal']}%)")
        print(f"{'─'*50}")
        for pocket, s in status.items():
            label = POCKETS[pocket]["label"]
            pri = POCKETS[pocket]["priority"]
            if s.get("total", 0) == 0:
                print(f"  [{pri[:1]}] {label:<35} — no data")
                continue
            filled = min(s.get("accepted", 0), 20)
            bar = "█" * filled + "░" * (20 - filled)
            print(f"  [{pri[:1]}] {label:<35} {bar}  "
                  f"{s.get('accepted',0):>2}✅ {s.get('revisar',0):>2}🔄 {s.get('rejected',0):>2}❌  "
                  f"total={s.get('total',0)}")
        print()
        return

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: set ANTHROPIC_API_KEY or use --api-key")
        sys.exit(1)

    # Load external anchor papers if provided (Change 2)
    anchor_papers = []
    if args.anchor_papers:
        try:
            anchor_papers = json.loads(Path(args.anchor_papers).read_text())
            print(f"Loaded {len(anchor_papers)} external anchor papers from {args.anchor_papers}")
        except Exception as e:
            print(f"Warning: could not load anchor papers: {e}")

    if args.pocket:
        # Change 9: --iterate triggers human-in-the-loop cycle
        if args.iterate:
            run_pocket_iteration(
                pocket=args.pocket,
                api_key=api_key,
                anchor_papers=anchor_papers,
                verbose=args.verbose,
            )
            return

        mode_tasks = {
            "search": (
                f"Search for new papers for the '{args.pocket}' pocket. "
                f"Get the pocket definition first, then run 3-4 of its curated queries across "
                f"the most relevant sources. After collecting, run enrich_metadata and "
                f"deduplicate_papers. Check coverage with evaluate_corpus_coverage. "
                f"Target: 60 ACCEPTED+REVIEW papers. Report findings."
            ),
            "review": (
                f"Load existing papers for the '{args.pocket}' pocket. Get the pocket definition. "
                f"Classify all papers using review_papers_with_ai (anchor-based, no rubric). "
                f"Then cluster_papers on ACCEPTED ones. Save results."
                + (f" External anchor papers: {json.dumps(anchor_papers)}" if anchor_papers else "")
            ),
            "full": (
                f"Run the full pipeline for the '{args.pocket}' pocket: "
                f"1) Check current corpus status. "
                f"2) Get pocket definition. "
                f"3) Search 2-3 sources using curated queries. "
                f"4) Enrich metadata via Crossref. "
                f"5) Deduplicate the combined results. "
                f"6) Check coverage score — target 60 ACCEPTED+REVIEW papers. If < 0.6, search more. "
                f"7) Classify papers with review_papers_with_ai (anchor-based). "
                f"8) Cluster ACCEPTED papers with cluster_papers. "
                f"9) Save everything. "
                f"10) Report: total_found, accepted, review, rejected, duplicates_removed."
                + (f"\nExternal anchor papers: {json.dumps(anchor_papers)}" if anchor_papers else "")
            ),
        }
        task = mode_tasks[args.mode]
    elif args.task:
        task = args.task
    elif args.interactive:
        print("BID-IA Agent — Interactive (Ctrl+C to exit)\n")
        while True:
            try:
                task = input("You: ").strip()
                if task:
                    run_agent(task, api_key, args.verbose)
                    print()
            except KeyboardInterrupt:
                print("\nGoodbye.")
                break
        return
    else:
        parser.print_help()
        return

    run_agent(task, api_key, args.verbose)


if __name__ == "__main__":
    main()