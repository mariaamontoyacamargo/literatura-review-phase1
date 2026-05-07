"""scrape_abstracts.py — Fetch abstracts by scraping paper URLs directly"""
import json, os, time, re, logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def get_soup(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        return None

def extract_abstract(url: str) -> str | None:
    domain = urlparse(url).netloc.replace("www.", "")
    soup = get_soup(url)
    if not soup:
        return None

    abstract = None

    # --- ArXiv ---
    if "arxiv.org" in domain:
        el = soup.find("blockquote", class_="abstract")
        if el:
            abstract = el.get_text(separator=" ").replace("Abstract:", "").strip()

    # --- Springer ---
    elif "springer.com" in domain:
        for sel in ["div.c-article-section__content p", "section#Abs1 p", 
                    "[data-article-section='abstract'] p", "div.Abstract p"]:
            el = soup.select_one(sel)
            if el:
                abstract = el.get_text(separator=" ").strip()
                break

    # --- ScienceDirect ---
    elif "sciencedirect.com" in domain:
        el = soup.find("div", {"class": re.compile("abstract.*content|Highlights.*abstract", re.I)})
        if not el:
            el = soup.find("p", {"id": re.compile("sp[0-9]+")})
        if not el:
            el = soup.select_one("div.abstract.author p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- SSRN ---
    elif "ssrn.com" in domain:
        el = soup.find("div", {"class": re.compile("abstract-text|ssrn-abstract", re.I)})
        if not el:
            el = soup.select_one("div[id='abstract-content'] p")
        if not el:
            el = soup.select_one(".abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Emerald ---
    elif "emerald.com" in domain:
        for sel in ["div.abstract__content", "section.article__section--abstract p",
                    "div[class*='NLM_abstract'] p"]:
            el = soup.select_one(sel)
            if el:
                abstract = el.get_text(separator=" ").strip()
                break

    # --- ACM Digital Library ---
    elif "dl.acm.org" in domain:
        el = soup.select_one("div.abstractSection p")
        if not el:
            el = soup.select_one("section#abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Taylor & Francis (tandfonline) ---
    elif "tandfonline.com" in domain:
        el = soup.select_one("div.abstractSection p")
        if not el:
            el = soup.find("div", {"class": re.compile("abstract", re.I)})
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- MDPI ---
    elif "mdpi.com" in domain:
        el = soup.select_one("div.art-abstract")
        if not el:
            el = soup.select_one("section.html-abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- SAGE ---
    elif "sagepub.com" in domain:
        el = soup.select_one("div.abstractSection p")
        if not el:
            el = soup.find("section", {"class": re.compile("abstract", re.I)})
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- ResearchGate ---
    elif "researchgate.net" in domain:
        el = soup.find("div", {"class": re.compile("abstract", re.I)})
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Wiley ---
    elif "wiley.com" in domain or "onlinelibrary.wiley.com" in domain:
        el = soup.select_one("div.article-section__content p")
        if not el:
            el = soup.select_one("section.article-section--abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- INFORMS ---
    elif "pubsonline.informs.org" in domain:
        el = soup.select_one("div.hlFld-Abstract p")
        if not el:
            el = soup.select_one("section#abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- IEEE ---
    elif "ieeexplore.ieee.org" in domain:
        el = soup.select_one("div.abstract-text p")
        if not el:
            # IEEE uses dynamic content - try meta tag
            meta = soup.find("meta", {"name": "Description"}) or soup.find("meta", {"property": "og:description"})
            if meta:
                abstract = meta.get("content","").strip()

    # --- NBER ---
    elif "nber.org" in domain:
        el = soup.select_one("div.page-header__intro p")
        if not el:
            el = soup.select_one("p.abstract")
        if not el:
            el = soup.find("div", {"id": "abstract"})
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Nature ---
    elif "nature.com" in domain:
        el = soup.select_one("div#Abs1-content p")
        if not el:
            el = soup.select_one("section[data-title='Abstract'] p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Oxford (academic.oup.com) ---
    elif "oup.com" in domain:
        el = soup.select_one("section.abstract p")
        if not el:
            el = soup.select_one("div.abstract p")
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- PREPRINTS.org ---
    elif "preprints.org" in domain:
        el = soup.select_one("div.abstract-content p")
        if not el:
            el = soup.find("p", {"class": re.compile("abstract", re.I)})
        if el:
            abstract = el.get_text(separator=" ").strip()

    # --- Generic fallback: look for <meta> description or common abstract patterns ---
    if not abstract:
        # Try og:description or meta description
        meta = soup.find("meta", {"property": "og:description"}) or \
               soup.find("meta", {"name": "description"}) or \
               soup.find("meta", {"name": "Description"})
        if meta:
            content = meta.get("content", "")
            if len(content) > 100:  # Meaningful length
                abstract = content.strip()

    if not abstract:
        # Try common CSS patterns as last resort
        for sel in ["#abstract", ".abstract", "[class*='abstract']", 
                    "section[id*='abstract']", "div[id*='abstract']"]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ").strip()
                if len(text) > 100:
                    abstract = text
                    break

    # Clean up
    if abstract:
        abstract = re.sub(r'\s+', ' ', abstract).strip()
        # Remove common prefixes
        abstract = re.sub(r'^(Abstract|ABSTRACT)[:\s]*', '', abstract).strip()
        if len(abstract) < 50:  # Too short, probably wrong
            return None

    return abstract

def enrich_pocket_scrape(pocket_name: str):
    f = f"data/{pocket_name}_papers_enriched.json"
    if not os.path.exists(f):
        return

    with open(f) as fp:
        papers = json.load(fp)

    scraped = 0
    failed = 0
    skipped = 0

    for i, paper in enumerate(papers):
        if paper.get("abstract"):
            skipped += 1
            continue

        url = paper.get("url") or paper.get("scholar_link", "")
        if not url or "books.google" in url or "proquest" in url:
            failed += 1
            continue

        title = paper.get("title","")[:60]
        abstract = extract_abstract(url)

        if abstract:
            paper["abstract"] = abstract
            scraped += 1
            logger.info(f"  [{i+1}] ✅ {title}...")
        else:
            paper["abstract"] = ""
            failed += 1
            logger.info(f"  [{i+1}] ❌ {title}...")

        time.sleep(0.5)

    # Save
    with open(f, "w") as fp:
        json.dump(papers, fp, indent=2, ensure_ascii=False)

    total_with = sum(1 for p in papers if p.get("abstract"))
    pct = int(total_with * 100 / max(len(papers),1))
    logger.info(f"\n  ✅ {pocket_name}: +{scraped} scraped | {failed} failed | {skipped} ya tenían | {pct}% cobertura total")
    return scraped, failed, total_with, len(papers)

if __name__ == "__main__":
    pockets = ["management","labor","evaluacion_experimental",
               "desigualdad","policy","human_machine_interaction","innovacion_difusion"]
    for pocket in pockets:
        logger.info(f"\n{'='*55}\n🔍 {pocket}\n{'='*55}")
        enrich_pocket_scrape(pocket)
    logger.info("\n🎉 Scraping complete!")
