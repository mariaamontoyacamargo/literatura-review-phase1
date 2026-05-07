"""build_network.py — Build citation + keyword network for BID-IA corpus.

Two types of edges:
  1. Citation edges (weight 5): Paper A's abstract explicitly cites Paper B.
     Extracted by Claude Haiku reading abstracts and matching against corpus catalog.
  2. Keyword edges (weight 1-3): Papers share keyword groups defined per pocket.

Only edges with combined weight >= 4 are included.

Usage:
  python scripts/build_network.py                        # uses ANTHROPIC_API_KEY env var
  python scripts/build_network.py --keywords-only        # no tokens, keyword edges only
  python scripts/build_network.py --api-key sk-ant-...
"""

import anthropic
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pockets import POCKETS

POCKET_COLORS = {
    "evaluacion_experimental": "#10b981",
    "human_machine_interaction": "#8b5cf6",
    "innovacion_difusion": "#ec4899",
    "labor": "#f59e0b",
    "desigualdad": "#ef4444",
    "management": "#6366f1",
    "policy": "#3b82f6",
}

# Keyword groups: papers sharing any group get keyword edges
KEYWORD_GROUPS = {
    "rct_exp":      ["rct", "randomized", "experiment", "quasi-experimental", "did", "difference-in-differences", "causal", "iv", "instrumental variable", "treatment effect"],
    "genai":        ["generative ai", "llm", "large language model", "gpt", "copilot", "chatgpt", "claude", "gemini", "foundation model"],
    "productivity": ["productivity", "output", "performance", "efficiency", "quality", "speed", "revenue"],
    "wage_labor":   ["wage", "salary", "employment", "job", "occupation", "task", "worker", "skill", "labor market"],
    "adoption":     ["adoption", "diffusion", "implementation", "deployment", "scale", "pilot", "digital transformation"],
    "inequality":   ["inequality", "heterogeneous", "skill premium", "digital divide", "gap", "distributional", "polarization"],
    "governance":   ["regulation", "governance", "policy", "compliance", "ethics", "accountability", "transparency"],
    "hmi":          ["human-ai", "complementarity", "over-reliance", "aversion", "trust", "calibration", "automation bias", "delegation"],
    "firm_org":     ["firm", "organization", "management", "capability", "change management", "process redesign", "complementary investment"],
}


def load_corpus(include_revisar: bool = False) -> list:
    """Load all reviewed papers from all pockets."""
    papers = []
    for pocket in POCKETS:
        for fname in [f"data/{pocket}_reviewed_enriched.json",
                      f"data/{pocket}_reviewed.json"]:
            f = Path(fname)
            if not f.exists():
                continue
            raw = json.loads(f.read_text())
            for p in raw:
                status = p.get("status", "")
                if status == "ACEPTADO" or (include_revisar and status == "REVISAR"):
                    meta = p.get("metadata", p)
                    abstract = (p.get("abstract") or
                                meta.get("summary") or
                                meta.get("abstract") or "")
                    authors = meta.get("authors", "")
                    if isinstance(authors, list):
                        authors = ", ".join(str(a) for a in authors[:3])
                    papers.append({
                        "id": len(papers),
                        "title": p.get("title", meta.get("title", "")),
                        "authors": authors,
                        "year": meta.get("year") or meta.get("published", "")[:4],
                        "venue": meta.get("venue", ""),
                        "abstract": abstract,
                        "url": meta.get("url", ""),
                        "score": p.get("score", 0),
                        "status": status,
                        "pocket": pocket,
                        "breakdown": p.get("breakdown", {}),
                        "criteria": p.get("criteria", []),
                    })
            break
    return papers


def keyword_edges(papers: list) -> list:
    """Compute keyword-based edges between papers."""
    edges = []

    def text(p):
        return f"{p['title']} {p['abstract']}".lower()

    def groups_for(p):
        t = text(p)
        return {g for g, kws in KEYWORD_GROUPS.items() if any(kw in t for kw in kws)}

    # Pre-compute groups and pocket
    for p in papers:
        p["_groups"] = groups_for(p)

    seen = set()
    for i, a in enumerate(papers):
        for j, b in enumerate(papers):
            if j <= i:
                continue
            key = (min(a["id"], b["id"]), max(a["id"], b["id"]))
            if key in seen:
                continue
            seen.add(key)

            shared_groups = a["_groups"] & b["_groups"]
            same_pocket = a["pocket"] == b["pocket"]

            weight = len(shared_groups)  # 1 pt per shared keyword group
            if same_pocket:
                weight += 2              # same pocket = stronger connection

            if weight >= 3:
                edges.append({
                    "from": a["id"],
                    "to": b["id"],
                    "value": weight,
                    "type": "keyword",
                    "shared_groups": list(shared_groups),
                })

    return edges


def citation_edges_with_ai(papers: list, client: anthropic.Anthropic) -> list:
    """Use Claude Haiku to extract citation mentions from abstracts."""
    # Build a short catalog: id -> short identifier for matching
    catalog = {
        p["id"]: {
            "id": p["id"],
            "title": p["title"][:80],
            "authors": p["authors"][:50],
            "year": str(p["year"] or ""),
        }
        for p in papers
    }

    catalog_text = "\n".join(
        f'[{c["id"]}] {c["authors"].split(",")[0].split()[-1] if c["authors"] else "?"} '
        f'({c["year"]}) — {c["title"]}'
        for c in catalog.values()
    )

    edges = []
    # Process in batches of 15 papers
    batch_size = 15
    for batch_start in range(0, len(papers), batch_size):
        batch = papers[batch_start: batch_start + batch_size]
        papers_with_abstract = [p for p in batch if len(p["abstract"]) > 100]
        if not papers_with_abstract:
            continue

        papers_text = "\n\n".join(
            f'PAPER_ID={p["id"]}\nTitle: {p["title"]}\n'
            f'Abstract: {p["abstract"][:600]}'
            for p in papers_with_abstract
        )

        prompt = f"""You are analyzing a corpus of academic papers about AI adoption in firms.
Your task: for each paper below, identify which OTHER papers from the CORPUS CATALOG are explicitly
cited or referenced in its abstract (by author name, year, or title).

CORPUS CATALOG (these are the only papers that matter):
{catalog_text}

PAPERS TO ANALYZE:
{papers_text}

Return a JSON array. For each paper, list the IDs it cites from the catalog:
[
  {{"paper_id": <int>, "cites": [<id1>, <id2>, ...]}},
  ...
]

Rules:
- Only include IDs from the catalog above.
- A citation exists if the abstract mentions the author's last name + year, or the paper title.
- If no citations are found for a paper, include it with "cites": [].
- Return ONLY the JSON array, no preamble.
"""
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            start, end = raw.find("["), raw.rfind("]") + 1
            if start == -1:
                continue
            results = json.loads(raw[start:end])
            for r in results:
                citing_id = r.get("paper_id")
                for cited_id in r.get("cites", []):
                    if citing_id != cited_id and cited_id in catalog:
                        edges.append({
                            "from": citing_id,
                            "to": cited_id,
                            "value": 5,
                            "type": "citation",
                        })
        except Exception as e:
            print(f"  Warning: batch {batch_start} failed — {e}")

        time.sleep(1)
        print(f"  Processed papers {batch_start}–{batch_start + len(batch) - 1}")

    return edges


def merge_edges(kw_edges: list, cit_edges: list) -> list:
    """Merge keyword and citation edges, combining weights for the same pair."""
    combined = {}
    for e in kw_edges:
        key = (min(e["from"], e["to"]), max(e["from"], e["to"]))
        combined[key] = {**e, "from": key[0], "to": key[1]}

    for e in cit_edges:
        key = (min(e["from"], e["to"]), max(e["from"], e["to"]))
        if key in combined:
            combined[key]["value"] += e["value"]
            combined[key]["type"] = "citation+keyword"
        else:
            combined[key] = {**e, "from": key[0], "to": key[1]}

    # Keep only edges with weight >= 4
    return [e for e in combined.values() if e["value"] >= 4]


def build_nodes(papers: list) -> list:
    """Build vis-network node objects."""
    nodes = []
    for p in papers:
        score = p.get("score", 5)
        size = 10 + max(0, score - 5) * 3
        ab = p["abstract"][:300] + ("…" if len(p["abstract"]) > 300 else "")
        nodes.append({
            "id": p["id"],
            "label": p["title"][:45] + ("…" if len(p["title"]) > 45 else ""),
            "title_full": p["title"],
            "pocket": p["pocket"],
            "pocket_label": POCKETS[p["pocket"]]["label"],
            "color": POCKET_COLORS[p["pocket"]],
            "score": score,
            "status": p["status"],
            "year": p["year"],
            "authors": p["authors"],
            "venue": p["venue"],
            "abstract": ab,
            "url": p["url"],
            "breakdown": p["breakdown"],
            "size": size,
        })
    return nodes


def main():
    parser = argparse.ArgumentParser(description="Build BID-IA citation + keyword network")
    parser.add_argument("--keywords-only", action="store_true",
                        help="Only keyword edges — no Claude, no tokens")
    parser.add_argument("--include-revisar", action="store_true",
                        help="Include REVISAR papers in the network (default: ACEPTADO only)")
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--output", default="data/bid_network.json")
    args = parser.parse_args()

    print("Loading corpus...")
    papers = load_corpus(include_revisar=args.include_revisar)
    print(f"  {len(papers)} papers loaded")

    print("Computing keyword edges...")
    kw_edges = keyword_edges(papers)
    print(f"  {len(kw_edges)} keyword edges (weight ≥ 3)")

    cit_edges = []
    if not args.keywords_only:
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("No ANTHROPIC_API_KEY found — skipping citation extraction.")
            print("Run with --keywords-only or set ANTHROPIC_API_KEY.")
        else:
            print("Extracting citation edges with Claude Haiku...")
            client = anthropic.Anthropic(api_key=api_key)
            cit_edges = citation_edges_with_ai(papers, client)
            print(f"  {len(cit_edges)} citation edges found")

    print("Merging edges...")
    edges = merge_edges(kw_edges, cit_edges)
    print(f"  {len(edges)} total edges after merge (weight ≥ 4)")

    nodes = build_nodes(papers)

    network = {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "total_papers": len(papers),
            "total_edges": len(edges),
            "citation_edges": len(cit_edges),
            "keyword_edges": len(kw_edges),
            "generated_at": __import__("datetime").datetime.now().isoformat(),
        },
    }

    Path(args.output).write_text(json.dumps(network, ensure_ascii=False, indent=2))
    print(f"\n✅ Network saved → {args.output}")
    print(f"   {len(nodes)} nodes  ·  {len(edges)} edges")
    citation_count = sum(1 for e in edges if "citation" in e.get("type", ""))
    print(f"   {citation_count} edges include citation signal")


if __name__ == "__main__":
    main()