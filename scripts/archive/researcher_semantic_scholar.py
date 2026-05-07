"""researcher_semantic_scholar.py - Search Semantic Scholar API (free, no key needed)

Semantic Scholar: 100 req/s, covers ArXiv + journals + working papers + citation graph.
Better metadata than Google Scholar, cleaner than raw ArXiv.

Usage:
  python scripts/researcher_semantic_scholar.py --pocket evaluacion_experimental --limit 60
  python scripts/researcher_semantic_scholar.py --author "Brynjolfsson" --pocket evaluacion_experimental
  python scripts/researcher_semantic_scholar.py --all  # run all 7 pockets
"""
import requests, json, time, argparse, os, sys
from pathlib import Path

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,abstract,authors,year,venue,citationCount,externalIds,openAccessPdf,fieldsOfStudy"

POCKET_QUERIES = {
    "evaluacion_experimental": [
        "generative AI productivity randomized controlled trial",
        "AI worker productivity causal experiment field",
        "LLM task experiment treatment effect knowledge worker",
        "generative AI firm productivity RCT DiD quasi-experimental",
        "AI adoption causal impact experiment LATAM developing",
    ],
    "human_machine_interaction": [
        "human AI complementarity collaboration experiment",
        "algorithm aversion over-reliance automation bias trust",
        "human machine interaction AI decision support productivity",
        "AI augmentation worker performance complementarity",
        "AI trust calibration over-reliance worker outcome",
    ],
    "innovacion_difusion": [
        "AI diffusion adoption firm productivity J-curve",
        "technology adoption barriers complementary investment firm",
        "AI adoption determinants SME organization",
        "generative AI firm adoption organizational change",
        "AI diffusion spillover productivity paradox",
    ],
    "labor": [
        "AI automation wage inequality labor market worker",
        "generative AI employment wage effect skill premium",
        "task automation AI worker displacement reallocation",
        "AI labor market developing country LATAM",
        "AI within-firm redistribution worker wage occupation",
    ],
    "desigualdad": [
        "AI inequality heterogeneous effects skill firm size",
        "AI wage gap polarization skill-biased technology",
        "AI digital divide access SME developing country",
        "AI inequality gender race distributional effects",
        "AI frontier firms laggard divergence productivity gap",
    ],
    "management": [
        "AI organizational adoption management capabilities firm",
        "AI implementation change management complementary investment",
        "AI adoption failure success organizational readiness",
        "AI strategy firm performance organizational capital",
        "AI pilot to production scale organizational",
    ],
    "policy": [
        "AI regulation policy adoption firm SME",
        "EU AI Act GDPR AI regulation compliance firm",
        "AI governance policy developing country LATAM",
        "AI public policy incentive adoption regulation effect",
        "AI algorithmic governance transparency accountability firm",
    ],
}

KEY_AUTHORS = [
    "Erik Brynjolfsson", "David Autor", "Daron Acemoglu",
    "Shakked Noy", "Fabrizio Dell'Acqua", "Nathan Otis",
    "Kjell Humlum", "Tyna Eloundou", "Sam Manning",
]


def search_papers(query, limit=20, year_start=2020, api_key=None):
    """Search Semantic Scholar for papers matching query."""
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": FIELDS,
        "year": f"{year_start}-",
    }
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        r = requests.get(f"{BASE}/paper/search", params=params, headers=headers, timeout=15)
        if r.status_code == 429:
            print("  Rate limit hit, waiting 10s...")
            time.sleep(10)
            r = requests.get(f"{BASE}/paper/search", params=params, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print(f"  Error searching '{query}': {e}")
        return []


def search_by_author(author_name, limit=20, year_start=2020, api_key=None):
    """Search papers by specific author."""
    params = {"query": author_name, "limit": 5, "fields": "authorId,name"}
    headers = {"x-api-key": api_key} if api_key else {}
    try:
        r = requests.get(f"{BASE}/author/search", params=params, headers=headers, timeout=10)
        r.raise_for_status()
        authors = r.json().get("data", [])
        if not authors:
            return []
        author_id = authors[0]["authorId"]
        # Get papers by this author
        params2 = {"fields": FIELDS, "limit": limit}
        r2 = requests.get(f"{BASE}/author/{author_id}/papers", params=params2, headers=headers, timeout=10)
        r2.raise_for_status()
        papers = r2.json().get("data", [])
        # Filter by year
        return [p for p in papers if (p.get("year") or 0) >= year_start]
    except Exception as e:
        print(f"  Error searching author '{author_name}': {e}")
        return []


def normalize_paper(p, pocket):
    """Normalize Semantic Scholar paper to project format."""
    authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:4])
    if len(p.get("authors") or []) > 4:
        authors += " et al."

    doi = (p.get("externalIds") or {}).get("DOI", "")
    arxiv_id = (p.get("externalIds") or {}).get("ArXiv", "")
    pdf_url = (p.get("openAccessPdf") or {}).get("url", "")
    url = pdf_url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else
                      f"https://doi.org/{doi}" if doi else "")

    return {
        "title": p.get("title", ""),
        "authors": authors,
        "year": p.get("year"),
        "venue": p.get("venue", ""),
        "abstract": p.get("abstract", ""),
        "url": url,
        "citations": p.get("citationCount", 0),
        "semantic_scholar_id": p.get("paperId", ""),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "source": "semantic_scholar",
        "pocket": pocket,
    }


def deduplicate(papers):
    """Remove duplicate papers by title similarity."""
    seen_titles = set()
    unique = []
    for p in papers:
        title_key = p["title"].lower().strip()[:60]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(p)
    return unique


def run_pocket(pocket, limit=60, api_key=None, include_authors=False):
    """Run full search for a pocket."""
    queries = POCKET_QUERIES.get(pocket, [])
    if not queries:
        print(f"Unknown pocket: {pocket}")
        return []

    print(f"\n{'='*60}")
    print(f"Pocket: {pocket}")
    print(f"{'='*60}")

    all_papers = []
    per_query = max(15, limit // len(queries))

    for q in queries:
        print(f"  Query: {q[:60]}...")
        results = search_papers(q, limit=per_query, api_key=api_key)
        normalized = [normalize_paper(p, pocket) for p in results if p.get("title")]
        all_papers.extend(normalized)
        print(f"    → {len(results)} papers")
        time.sleep(1)  # Be polite to API

    if include_authors:
        print(f"  Searching key authors...")
        for author in KEY_AUTHORS[:5]:
            results = search_by_author(author, limit=10, api_key=api_key)
            for p in results:
                if p.get("abstract"):  # Only add if has abstract
                    all_papers.append(normalize_paper(p, pocket))
            time.sleep(0.5)

    deduped = deduplicate(all_papers)
    print(f"  Total unique: {len(deduped)} (from {len(all_papers)} raw)")

    # Save
    out_path = f"data/{pocket}_papers_ss.json"
    with open(out_path, "w") as f:
        json.dump(deduped[:limit], f, ensure_ascii=False, indent=2)
    print(f"  Saved → {out_path}")

    return deduped[:limit]


def merge_with_existing(pocket, new_papers):
    """Merge new Semantic Scholar papers with existing enriched papers."""
    existing_path = f"data/{pocket}_papers_enriched.json"
    if not os.path.exists(existing_path):
        print(f"  No existing enriched file for {pocket}, saving as new")
        with open(f"data/{pocket}_papers_enriched.json", "w") as f:
            json.dump(new_papers, f, ensure_ascii=False, indent=2)
        return new_papers

    with open(existing_path) as f:
        existing = json.load(f)

    existing_titles = {p["title"].lower().strip()[:60] for p in existing}
    added = 0
    for p in new_papers:
        key = p["title"].lower().strip()[:60]
        if key and key not in existing_titles:
            existing.append(p)
            existing_titles.add(key)
            added += 1

    with open(existing_path, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  Merged: +{added} new papers → {len(existing)} total in {existing_path}")
    return existing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Semantic Scholar for BID-IA pockets")
    parser.add_argument("--pocket", help="Specific pocket to search")
    parser.add_argument("--all", action="store_true", help="Search all pockets")
    parser.add_argument("--author", help="Search by specific author name")
    parser.add_argument("--limit", type=int, default=60, help="Max papers per pocket")
    parser.add_argument("--merge", action="store_true", help="Merge results with existing enriched files")
    parser.add_argument("--api-key", help="Semantic Scholar API key (optional, increases rate limit)")
    args = parser.parse_args()

    pockets_to_run = list(POCKET_QUERIES.keys()) if args.all else ([args.pocket] if args.pocket else [])

    if not pockets_to_run and not args.author:
        print("Specify --pocket POCKET_NAME, --all, or --author NAME")
        print(f"Available pockets: {', '.join(POCKET_QUERIES.keys())}")
        sys.exit(1)

    for pocket in pockets_to_run:
        papers = run_pocket(pocket, limit=args.limit, api_key=args.api_key)
        if args.merge:
            merge_with_existing(pocket, papers)

    if args.author:
        print(f"\nSearching author: {args.author}")
        results = search_by_author(args.author, limit=30, api_key=args.api_key)
        print(f"Found {len(results)} papers")
        for p in results[:10]:
            print(f"  {p.get('year')} | {p.get('title','')[:70]}")