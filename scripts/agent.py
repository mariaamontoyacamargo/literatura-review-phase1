"""agent.py — BID-IA Literature Review Agent

Agentic CLI: Claude (Sonnet) orchestrates the pipeline, deciding which tools to call.
Sub-calls to Claude Haiku execute actual AI review and synthesis.
Search covers 4 sources: Semantic Scholar, NBER, OpenAlex, ArXiv.

Usage:
  python scripts/agent.py --status
  python scripts/agent.py --pocket labor
  python scripts/agent.py --pocket evaluacion_experimental --mode search
  python scripts/agent.py "what gaps exist in our current corpus?"
  python scripts/agent.py --interactive
"""

import anthropic
import argparse
import json
import os
import re
import sys
import time
import textwrap
from datetime import datetime
from pathlib import Path

# Pocket definitions and rubric live in pockets.py
sys.path.insert(0, str(Path(__file__).parent))
from pockets import POCKETS, RUBRIC, PROJECT_CONTEXT


# ── Search helpers ────────────────────────────────────────────────────────────

def _search_semantic_scholar(query: str, limit: int, year_start: int) -> list:
    import requests
    BASE = "https://api.semanticscholar.org/graph/v1"
    FIELDS = "paperId,title,abstract,authors,year,venue,citationCount,externalIds,openAccessPdf"
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS, "year": f"{year_start}-"}
    try:
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
            doi, arxiv_id = ids.get("DOI", ""), ids.get("ArXiv", "")
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
                "citations": p.get("citationCount", 0),
                "source": "semantic_scholar",
            })
        return results
    except Exception as e:
        return [{"error": f"Semantic Scholar: {e}"}]


def _search_nber(query: str, limit: int) -> list:
    import requests
    try:
        r = requests.get(
            "https://www.nber.org/api/v1/working_paper/search",
            params={"q": query, "facet": "series:w", "start": 0,
                    "perPage": min(limit, 30), "sortBy": "score"},
            timeout=15, headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        results = []
        for p in r.json().get("results", []):
            if not p.get("title"):
                continue
            nber_id = p.get("url", "").split("/")[-1].strip("/")
            authors_list = p.get("authors") or []
            authors = ", ".join(
                f"{a.get('first_name','')} {a.get('last_name','')}".strip()
                for a in authors_list[:4]
            )
            m = re.search(r"(\d{4})", str(p.get("pubDate") or ""))
            year = int(m.group(1)) if m else None
            results.append({
                "title": p.get("title", ""),
                "authors": authors,
                "year": year,
                "venue": "NBER Working Paper",
                "abstract": p.get("abstract", ""),
                "url": f"https://www.nber.org/papers/{nber_id}" if nber_id else "",
                "citations": None,
                "source": "nber",
            })
        return results
    except Exception as e:
        return [{"error": f"NBER: {e}"}]


def _search_openalex(query: str, limit: int, year_start: int) -> list:
    """OpenAlex: free, 100k req/day, 240M works, best for citation counts and DOIs."""
    import requests
    try:
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
            authors = ", ".join(
                a.get("author", {}).get("display_name", "") for a in authors_list[:4]
            )
            if len(authors_list) > 4:
                authors += " et al."
            # Reconstruct abstract from inverted index
            abstract = ""
            inv = p.get("abstract_inverted_index") or {}
            if inv:
                words = sorted(
                    [(pos, word) for word, positions in inv.items() for pos in positions]
                )
                abstract = " ".join(w for _, w in words[:200])
            loc = p.get("primary_location") or {}
            source = (loc.get("source") or {}).get("display_name", "")
            doi = p.get("doi", "")
            oa_url = (p.get("open_access") or {}).get("oa_url", "")
            url = oa_url or (f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else "")
            results.append({
                "title": p.get("title", ""),
                "authors": authors,
                "year": p.get("publication_year"),
                "venue": source,
                "abstract": abstract,
                "url": url,
                "citations": p.get("cited_by_count", 0),
                "source": "openalex",
            })
        return results
    except Exception as e:
        return [{"error": f"OpenAlex: {e}"}]


def _search_arxiv(query: str, limit: int, year_start: int) -> list:
    """ArXiv API: best for CS papers 2024-2026 before journal publication."""
    import requests, urllib.parse
    try:
        # ArXiv has its own query syntax
        search_query = urllib.parse.quote(f"all:{query}")
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(limit, 50),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        r = requests.get("http://export.arxiv.org/api/query", params=params, timeout=20)
        r.raise_for_status()
        # Parse Atom XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        results = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.find("atom:title", ns) or {}).text or ""
            title = title.strip().replace("\n", " ")
            abstract = (entry.find("atom:summary", ns) or {}).text or ""
            abstract = abstract.strip().replace("\n", " ")
            published = (entry.find("atom:published", ns) or {}).text or ""
            year = int(published[:4]) if published else None
            if year and year < year_start:
                continue
            authors_els = entry.findall("atom:author", ns)
            authors = ", ".join(
                (a.find("atom:name", ns) or {}).text or "" for a in authors_els[:4]
            )
            if len(authors_els) > 4:
                authors += " et al."
            arxiv_id = (entry.find("atom:id", ns) or {}).text or ""
            arxiv_id = arxiv_id.replace("http://arxiv.org/abs/", "").strip()
            results.append({
                "title": title,
                "authors": authors,
                "year": year,
                "venue": "arXiv",
                "abstract": abstract,
                "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                "citations": None,
                "source": "arxiv",
            })
        return results
    except Exception as e:
        return [{"error": f"ArXiv: {e}"}]


# ── Corpus helpers ─────────────────────────────────────────────────────────────

def get_corpus_status() -> dict:
    status = {}
    total_accepted = total_papers = 0
    for pocket in POCKETS:
        for fname in [f"data/{pocket}_reviewed_enriched.json",
                      f"data/{pocket}_reviewed.json",
                      f"data/{pocket}_papers_enriched.json"]:
            f = Path(fname)
            if f.exists():
                papers = json.loads(f.read_text())
                accepted = sum(1 for p in papers if p.get("status") == "ACEPTADO")
                status[pocket] = {
                    "total": len(papers),
                    "accepted": accepted,
                    "revisar": sum(1 for p in papers if p.get("status") == "REVISAR"),
                    "rejected": sum(1 for p in papers if p.get("status") == "RECHAZADO"),
                    "with_abstract": sum(
                        1 for p in papers
                        if p.get("abstract") or p.get("metadata", {}).get("abstract")
                    ),
                    "source": f.name,
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
    for fname in [f"data/{pocket}_reviewed_enriched.json",
                  f"data/{pocket}_reviewed.json",
                  f"data/{pocket}_papers_enriched.json"]:
        f = Path(fname)
        if f.exists():
            papers = json.loads(f.read_text())
            if status_filter:
                papers = [p for p in papers if p.get("status") == status_filter]
            return papers[:50]
    return []


def save_papers(pocket: str, papers: list, mode: str = "merge") -> dict:
    out_path = Path(f"data/{pocket}_reviewed_enriched.json")
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


# ── Tool definitions for Claude ──────────────────────────────────────────────

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
            "Returns the full definition of a pocket: central research question (from the BID deck), "
            "why it matters for the Guatiguará RCT, the 8 curated search queries, anchor papers, "
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
            "Search for academic papers. Four sources available:\n"
            "- 'semantic_scholar': broad coverage (ArXiv + journals + WPs). Good for CS/interdisciplinary.\n"
            "- 'nber': NBER working papers. Best for economics: Autor, Acemoglu, Brynjolfsson, Humlum.\n"
            "- 'openalex': 240M works, free, best citation counts. Good for journals + social science.\n"
            "- 'arxiv': CS/AI preprints 2024-2026. Best for very recent LLM productivity papers.\n\n"
            "Use the pocket's curated queries (from get_pocket_definition) as your starting point. "
            "Search multiple sources for HIGH priority pockets. Use year_start=2022 for GenAI focus."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": ["semantic_scholar", "nber", "openalex", "arxiv"],
                    "default": "semantic_scholar",
                },
                "limit": {"type": "integer", "default": 20},
                "year_start": {"type": "integer", "default": 2020},
            },
            "required": ["query"],
        },
    },
    {
        "name": "review_papers_with_ai",
        "description": (
            "You (Claude Haiku) review a list of papers against the pocket's rubric and acceptance criteria. "
            "For each paper: read the abstract, apply rubric (methodology 0-4, causal 0-2, top-tier 0-2, "
            "novelty -1/0/1, relevance 0-2), check each of the 5 acceptance criteria, compute total score, "
            "assign ACEPTADO/REVISAR/RECHAZADO. Use real academic judgment — a paper with high methodology "
            "but zero relevance to the pocket's question must be RECHAZADO."
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
        "name": "synthesize_papers",
        "description": (
            "You (Claude Haiku) synthesize accepted papers: extract main finding, methodology type, "
            "outcome measured, sample context, effect size (if available), limitations, LATAM relevance, "
            "and connections to other papers in the corpus. Only synthesize ACCEPTED papers."
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
        time.sleep(0.5)  # polite delay

        if source == "semantic_scholar":
            return json.dumps(_search_semantic_scholar(query, limit, year_start), ensure_ascii=False)
        if source == "nber":
            return json.dumps(_search_nber(query, limit), ensure_ascii=False)
        if source == "openalex":
            return json.dumps(_search_openalex(query, limit, year_start), ensure_ascii=False)
        if source == "arxiv":
            return json.dumps(_search_arxiv(query, limit, year_start), ensure_ascii=False)
        return json.dumps({"error": f"Unknown source: {source}"})

    if name == "load_papers":
        return json.dumps(load_papers(inputs["pocket"], inputs.get("status_filter")), ensure_ascii=False)

    if name == "save_papers":
        return json.dumps(save_papers(inputs["pocket"], inputs["papers"], inputs.get("mode", "merge")))

    if name == "review_papers_with_ai":
        pocket = inputs["pocket"]
        papers = inputs["papers"][:30]
        p = POCKETS[pocket]

        papers_text = "\n\n".join(
            f"PAPER {i+1}:\nTitle: {p2.get('title','')}\n"
            f"Authors: {p2.get('authors','')} | Year: {p2.get('year','')} | "
            f"Venue: {p2.get('venue','')} | Citations: {p2.get('citations','N/A')}\n"
            f"Abstract: {(p2.get('abstract') or 'NO ABSTRACT — score based on title only')[:600]}"
            for i, p2 in enumerate(papers)
        )

        criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(p["accept_criteria"]))
        prompt = f"""You are a rigorous academic reviewer for the BID-IA project on AI adoption in firms (Colombia/LATAM).

POCKET: {pocket} — {p["label"]}
CENTRAL QUESTION: {p["question"]}

{RUBRIC}

ACCEPTANCE CRITERIA FOR THIS POCKET:
{criteria_text}

IMPORTANT: A paper with methodology=4 but relevance=0 MUST be RECHAZADO.
Relevance to the pocket's central question is non-negotiable.

For each paper, return a JSON object:
{{
  "title": "<exact title>",
  "score": <int 0-11>,
  "status": "<ACEPTADO|REVISAR|RECHAZADO>",
  "breakdown": {{"methodology": <0-4>, "causalidity": <0-2>, "top_tier": <0-2>, "novelty": <-1|0|1>, "relevance": <0-2>}},
  "criteria": [{{"key": "c1", "desc": "<criterion text>", "met": <true|false>}}, ...],
  "review_note": "<1-2 sentence justification>"
}}

Return ONLY a JSON array, one object per paper. No preamble.

PAPERS:
{papers_text}
"""
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start, end = raw.find("["), raw.rfind("]") + 1
        if start == -1 or end <= start:
            return json.dumps({"error": "Could not parse review", "raw": raw[:500]})
        reviews = json.loads(raw[start:end])
        review_map = {r["title"].lower()[:60]: r for r in reviews}

        reviewed = []
        for p2 in papers:
            key = p2.get("title", "").lower()[:60]
            rev = review_map.get(key)
            if rev:
                merged = {**p2, **rev, "pocket": pocket, "reviewed_at": datetime.now().isoformat()}
                if "metadata" not in merged:
                    skip = {"score", "status", "breakdown", "criteria", "review_note", "reviewed_at", "pocket"}
                    merged["metadata"] = {k: v for k, v in p2.items() if k not in skip}
                reviewed.append(merged)
            else:
                reviewed.append(p2)
        return json.dumps(reviewed, ensure_ascii=False)

    if name == "synthesize_papers":
        pocket = inputs["pocket"]
        papers = inputs["papers"][:20]
        p = POCKETS[pocket]

        papers_text = "\n\n".join(
            f"PAPER {i+1} (score {p2.get('score','?')}):\nTitle: {p2.get('title','')}\n"
            f"Authors: {p2.get('authors','')} | Year: {p2.get('year','')} | Venue: {p2.get('venue','')}\n"
            f"Abstract: {(p2.get('abstract') or p2.get('metadata', {}).get('abstract', 'NO ABSTRACT'))[:500]}"
            for i, p2 in enumerate(papers)
        )

        prompt = f"""Synthesize these papers for the BID-IA project on AI adoption in firms (Colombia/LATAM).

POCKET: {pocket} — {p["label"]}
CENTRAL QUESTION: {p["question"]}
PROJECT: First RCT of AI adoption in LATAM SMEs (Guatiguará). This literature informs the design.

For each paper, return a JSON synthesis:
{{
  "title": "<exact title>",
  "synthesis": {{
    "main_finding": "<1 sentence: the key empirical result>",
    "methodology": "<RCT|DiD|IV|panel|observational|framework|meta-analysis|other>",
    "outcome_measured": "<what was measured: productivity, wage, adoption rate, etc.>",
    "sample_context": "<who/where: e.g. call center workers in US, BCG consultants, US manufacturing>",
    "effect_size": "<if reported: e.g. +15% productivity, -0.3 log wage, or 'not reported'>",
    "limitations": "<main limitation in 1 sentence>",
    "latam_relevance": "<high|medium|low|none — one sentence why>",
    "design_lesson": "<what this paper teaches for designing the Guatiguará RCT, or 'N/A'>",
    "connects_to": ["<title of related paper in this same list, if any>"]
  }}
}}

Return ONLY a JSON array. No preamble.

PAPERS:
{papers_text}
"""
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start, end = raw.find("["), raw.rfind("]") + 1
        if start == -1 or end <= start:
            return json.dumps({"error": "Could not parse synthesis", "raw": raw[:300]})
        syntheses = json.loads(raw[start:end])
        synth_map = {s["title"].lower()[:60]: s["synthesis"] for s in syntheses}
        enriched = []
        for p2 in papers:
            key = p2.get("title", "").lower()[:60]
            s = synth_map.get(key)
            enriched.append({**p2, "synthesis": s} if s else p2)
        return json.dumps(enriched, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are the BID-IA Literature Review Agent for Fedesarrollo & BID.

{PROJECT_CONTEXT}

HOW TO APPROACH TASKS:
1. Start with get_corpus_status — understand what exists, what's missing, what's below target.
2. For any pocket, call get_pocket_definition first — it has the exact curated queries and criteria.
3. When searching: use the pocket's curated queries as your starting point. Search 2-3 sources for
   HIGH priority pockets. Use year_start=2022 for generative AI focus; 2020 for broader coverage.
   Source strategy: NBER for economics pockets (labor, desigualdad, evaluacion_experimental);
   ArXiv for recent CS/AI papers; OpenAlex for citation counts; Semantic Scholar for breadth.
4. When reviewing: apply real academic judgment. A paper scoring high on methodology but with
   zero relevance to the pocket's question is RECHAZADO. Don't let methodology override relevance.
5. After reviewing, always save before ending the task.
6. Synthesize only ACCEPTED papers. The synthesis must be useful for designing the Guatiguará RCT.

COMMUNICATION: Be concise. Report counts clearly after each tool call.
"Found 18 papers across 2 sources. Reviewed: 7 ACEPTADO, 4 REVISAR, 7 RECHAZADO. Saved."
"""


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_agent(task: str, api_key: str, verbose: bool = False):
    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": task}]

    print(f"\n{'─'*60}")
    print(f"TASK: {task}")
    print(f"{'─'*60}\n")

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

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
                        if parsed and "error" in parsed[0]:
                            print(f"   ❌ {parsed[0]['error']}")
                        else:
                            print(f"   → {len(parsed)} items")
                    elif isinstance(parsed, dict) and "_summary" in parsed:
                        s = parsed["_summary"]
                        print(f"   → {s['total_accepted']}/{s['goal']} accepted ({s['pct_goal']}%)")
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

    print(f"\n{'─'*60}\nDone.\n")


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
    parser.add_argument("--mode", choices=["search", "review", "synthesize", "full"], default="full")
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

    if args.pocket:
        mode_tasks = {
            "search": (
                f"Search for new papers for the '{args.pocket}' pocket. "
                f"Get the pocket definition first, then run 3-4 of its curated queries across "
                f"the most relevant sources. Deduplicate and report what you found."
            ),
            "review": (
                f"Load unreviewed papers for the '{args.pocket}' pocket, review them against "
                f"the pocket's rubric and acceptance criteria, and save the results."
            ),
            "synthesize": (
                f"Load ACCEPTED papers for the '{args.pocket}' pocket, synthesize them "
                f"(extract findings, methodology, effect sizes, LATAM relevance, design lessons), "
                f"and save the enriched results."
            ),
            "full": (
                f"Run the full pipeline for the '{args.pocket}' pocket: "
                f"1) Check current corpus status. "
                f"2) Get pocket definition and curated queries. "
                f"3) Search 2-3 sources for new papers. "
                f"4) Review all new papers against the rubric. "
                f"5) Synthesize the accepted ones. "
                f"6) Save everything. "
                f"7) Report: what was found, what was accepted, what gaps remain."
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