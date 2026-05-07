"""researcher_nber.py - Search NBER Working Papers (free, no key needed)

NBER is the primary source for economics working papers: Brynjolfsson, Autor,
Acemoglu, Humlum, etc. publish here before journals.

Usage:
  python scripts/researcher_nber.py --pocket labor --limit 40
  python scripts/researcher_nber.py --all
"""
import requests, json, time, argparse, sys, re
from pathlib import Path

NBER_SEARCH = "https://www.nber.org/api/v1/working_paper/search"
NBER_PAPER  = "https://www.nber.org/papers"

POCKET_QUERIES = {
    "evaluacion_experimental": [
        "generative AI productivity experiment randomized",
        "AI worker productivity RCT causal field experiment",
        "large language model productivity experiment",
    ],
    "human_machine_interaction": [
        "human AI interaction complementarity algorithm",
        "AI decision support human judgment",
        "AI trust over-reliance worker",
    ],
    "innovacion_difusion": [
        "AI adoption diffusion firm productivity",
        "technology diffusion AI complementary investment",
        "AI adoption organizational J-curve",
    ],
    "labor": [
        "artificial intelligence labor market employment wage",
        "AI automation task reallocation wage inequality",
        "generative AI labor displacement skill premium",
        "AI worker productivity wage within-firm",
    ],
    "desigualdad": [
        "AI inequality skill premium wage polarization",
        "AI heterogeneous effects worker firm size",
        "technology adoption inequality distributional",
    ],
    "management": [
        "AI firm adoption management capabilities",
        "AI organizational change complementary investment",
        "AI adoption determinants firm strategy",
    ],
    "policy": [
        "AI regulation policy adoption firm",
        "AI governance policy labor market",
        "AI public policy developing country",
    ],
}


def search_nber(query, limit=30):
    """Search NBER working papers API."""
    params = {
        "q": query,
        "facet": "series:w",
        "start": 0,
        "perPage": min(limit, 30),
        "sortBy": "score",
    }
    try:
        r = requests.get(NBER_SEARCH, params=params, timeout=15,
                         headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as e:
        print(f"  Error: {e}")
        return []


def normalize_nber(p, pocket):
    """Normalize NBER result to project format."""
    nber_id = p.get("url", "").split("/")[-1].strip("/")
    url = f"https://www.nber.org/papers/{nber_id}" if nber_id else p.get("url", "")
    authors = ", ".join(
        f"{a.get('first_name','')} {a.get('last_name','')}".strip()
        for a in (p.get("authors") or [])[:4]
    )
    year = None
    date_str = p.get("pubDate") or p.get("date") or ""
    m = re.search(r"(\d{4})", str(date_str))
    if m:
        year = int(m.group(1))

    return {
        "title": p.get("title", ""),
        "authors": authors,
        "year": year,
        "venue": "NBER Working Paper",
        "abstract": p.get("abstract", ""),
        "url": url,
        "citations": None,
        "nber_id": nber_id,
        "source": "nber",
        "pocket": pocket,
    }


def run_pocket(pocket, limit=40):
    queries = POCKET_QUERIES.get(pocket, [])
    print(f"\n{'='*60}\nPocket: {pocket}\n{'='*60}")
    all_papers = []
    per_q = max(10, limit // len(queries))

    for q in queries:
        print(f"  Query: {q[:60]}...")
        results = search_nber(q, limit=per_q)
        normalized = [normalize_nber(r, pocket) for r in results if r.get("title")]
        all_papers.extend(normalized)
        print(f"    → {len(results)} papers")
        time.sleep(1)

    # Deduplicate
    seen = set()
    deduped = []
    for p in all_papers:
        key = p["title"].lower()[:60]
        if key and key not in seen:
            seen.add(key); deduped.append(p)

    deduped = deduped[:limit]
    out = f"data/{pocket}_papers_nber.json"
    with open(out, "w") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(deduped)} papers → {out}")
    return deduped


def merge_with_existing(pocket, new_papers):
    path = f"data/{pocket}_papers_enriched.json"
    existing = json.load(open(path)) if Path(path).exists() else []
    existing_keys = {p["title"].lower()[:60] for p in existing}
    added = 0
    for p in new_papers:
        key = p["title"].lower()[:60]
        if key and key not in existing_keys:
            existing.append(p); existing_keys.add(key); added += 1
    with open(path, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"  Merged +{added} NBER papers → {len(existing)} total in {path}")
    return existing


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pocket")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()

    pockets = list(POCKET_QUERIES.keys()) if args.all else ([args.pocket] if args.pocket else [])
    if not pockets:
        print(f"Use --pocket NAME or --all. Pockets: {', '.join(POCKET_QUERIES.keys())}")
        sys.exit(1)

    for pocket in pockets:
        papers = run_pocket(pocket, limit=args.limit)
        if args.merge:
            merge_with_existing(pocket, papers)