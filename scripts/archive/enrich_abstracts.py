"""enrich_abstracts.py — Fetch abstracts using ArXiv summary + OpenAlex API"""
import json, time, requests, os, re, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "BID-IA LitReview m.montoyac@uniandes.edu.co"}

def clean_title(t: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'([a-z])([A-Z])', r'\1 \2', t)).strip()

def reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    words = sorted([(pos, w) for w, positions in inverted_index.items() for pos in positions])
    return " ".join(w for _, w in words)

def fetch_openalex(title: str) -> dict | None:
    cleaned = clean_title(title)
    try:
        r = requests.get("https://api.openalex.org/works", params={
            "filter": f"title.search:{cleaned[:90]}",
            "per_page": 5,
            "select": "title,abstract_inverted_index,cited_by_count,publication_year,primary_location,doi"
        }, timeout=12, headers=HEADERS)
        r.raise_for_status()
        results = r.json().get("results", [])
        # Prefer exact title match with abstract
        cleaned_lower = cleaned.lower().strip()
        for p in results:
            if p.get("title","").lower().strip() == cleaned_lower and p.get("abstract_inverted_index"):
                return p
        # Fallback: first result with abstract
        for p in results:
            if p.get("abstract_inverted_index"):
                return p
        return None
    except Exception as e:
        logger.warning(f"  OpenAlex error: {e}")
        return None

def enrich_pocket(pocket_name: str):
    combined_file = f"data/{pocket_name}_papers_combined.json"
    if not os.path.exists(combined_file):
        return

    with open(combined_file) as f:
        papers = json.load(f)

    enriched = 0
    already_have = 0
    not_found = 0

    for i, paper in enumerate(papers):
        # Use ArXiv summary directly
        if paper.get("summary") and not paper.get("abstract"):
            paper["abstract"] = paper["summary"]
            already_have += 1
            continue
        if paper.get("abstract"):
            already_have += 1
            continue

        title = paper.get("title", "").strip()
        if not title:
            not_found += 1
            continue

        result = fetch_openalex(title)
        if result and result.get("abstract_inverted_index"):
            paper["abstract"] = reconstruct_abstract(result["abstract_inverted_index"])
            if not paper.get("citations") and result.get("cited_by_count"):
                paper["citations"] = result["cited_by_count"]
            if not paper.get("doi") and result.get("doi"):
                paper["doi"] = result["doi"]
            enriched += 1
        else:
            paper["abstract"] = ""
            not_found += 1

        time.sleep(0.1)  # OpenAlex: 100 req/s polite limit

    output_file = f"data/{pocket_name}_papers_enriched.json"
    with open(output_file, "w") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    pct = int((already_have + enriched) * 100 / max(len(papers),1))
    logger.info(f"  ✅ {pocket_name}: {already_have} ya tenían | +{enriched} OpenAlex | {not_found} no encontrados | {pct}% cobertura")

if __name__ == "__main__":
    pockets = ["management","labor","evaluacion_experimental",
               "desigualdad","policy","human_machine_interaction","innovacion_difusion"]
    for pocket in pockets:
        logger.info(f"\n{'='*50}\n🔍 {pocket}\n{'='*50}")
        enrich_pocket(pocket)
    logger.info("\n🎉 Done!")
