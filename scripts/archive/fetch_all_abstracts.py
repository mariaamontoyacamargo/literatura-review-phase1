"""fetch_all_abstracts.py — 3 strategies in parallel: Unpaywall, credentials, Claude API"""
import json, os, re, time, logging, requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── STRATEGY 1: Unpaywall ──────────────────────────────────────────────────
def get_doi_from_url(url: str) -> str | None:
    """Extract DOI from URL patterns."""
    patterns = [
        r'doi\.org/(.+)',
        r'10\.\d{4,}/[^\s&?#]+',
        r'doi=([^&]+)',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            doi = m.group(1) if '(' in pat else m.group()
            return doi.rstrip('/')
    return None

def unpaywall_fetch(doi: str, email="m.montoyac@uniandes.edu.co") -> str | None:
    """Get open-access abstract via Unpaywall → CrossRef fallback."""
    # First try CrossRef for abstract (fastest)
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}",
                        params={"mailto": email}, timeout=10)
        data = r.json().get("message", {})
        abstract = data.get("abstract", "")
        if abstract:
            # CrossRef returns XML-like tags sometimes
            abstract = re.sub(r'<[^>]+>', '', abstract).strip()
            if len(abstract) > 80:
                return abstract
    except: pass
    
    # Try Unpaywall for open-access PDF URL, then fetch that
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}",
                        params={"email": email}, timeout=10)
        data = r.json()
        oa_url = data.get("best_oa_location", {})
        if oa_url:
            pdf_url = oa_url.get("url_for_landing_page") or oa_url.get("url")
            if pdf_url and "pdf" not in pdf_url.lower():
                from scripts.scrape_abstracts import extract_abstract
                return extract_abstract(pdf_url)
    except: pass
    return None

# ─── STRATEGY 2: Institutional credentials (Uniandes EZProxy) ──────────────
def with_credentials(url: str, username: str, password: str) -> str | None:
    """Access paywalled papers through Uniandes EZProxy."""
    # Uniandes proxy wraps URLs like: https://login.ezproxy.uniandes.edu.co/login?url=ORIGINAL_URL
    proxy_url = f"https://login.ezproxy.uniandes.edu.co/login?url={url}"
    session = requests.Session()
    
    try:
        # Step 1: Get the login page
        r = session.get(proxy_url, headers=HEADERS_BROWSER, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Step 2: Find login form and submit
        form = soup.find("form")
        if not form:
            return None
            
        action = form.get("action", proxy_url)
        if not action.startswith("http"):
            action = f"https://login.ezproxy.uniandes.edu.co{action}"
        
        form_data = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            val = inp.get("value", "")
            if name:
                form_data[name] = val
        
        # Fill credentials
        for field in ["user", "username", "login", "j_username"]:
            if field in form_data: form_data[field] = username
        for field in ["pass", "password", "j_password"]:
            if field in form_data: form_data[field] = password
        
        r2 = session.post(action, data=form_data, headers=HEADERS_BROWSER, timeout=15)
        
        # Step 3: Extract abstract from authenticated page
        soup2 = BeautifulSoup(r2.text, "html.parser")
        from scripts.scrape_abstracts import extract_abstract
        
        # Try generic extraction on authenticated page
        for sel in ["div.abstract", ".abstract-content", "#abstract", 
                    "section[id*='abstract']", "p.abstract", ".abstractSection p"]:
            el = soup2.select_one(sel)
            if el:
                text = el.get_text(" ").strip()
                if len(text) > 80:
                    return re.sub(r'\s+', ' ', text).strip()
        return None
    except Exception as e:
        logger.debug(f"Credentials error: {e}")
        return None

# ─── STRATEGY 3: Claude API extraction ─────────────────────────────────────
def claude_extract(url: str, title: str, client: Anthropic) -> str | None:
    """Fetch page HTML and use Claude to extract the abstract."""
    try:
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=15)
        r.raise_for_status()
        # Truncate HTML to avoid huge tokens
        html = r.text[:15000]
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts, styles, nav
        for tag in soup(["script","style","nav","footer","header","aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:6000]
    except:
        return None
    
    if not text or len(text) < 200:
        return None
    
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Extract ONLY the abstract from this academic paper page. 
Paper title: {title}

Page text:
{text}

Return ONLY the abstract text, nothing else. If there is no abstract, return "NO_ABSTRACT"."""
            }]
        )
        result = msg.content[0].text.strip()
        if result == "NO_ABSTRACT" or len(result) < 80:
            return None
        return result
    except Exception as e:
        logger.debug(f"Claude error: {e}")
        return None

# ─── MAIN ORCHESTRATOR ──────────────────────────────────────────────────────
def run(use_credentials=False, username="", password="",
        use_claude=False, claude_api_key="",
        pocket_filter=None):
    
    claude_client = Anthropic(api_key=claude_api_key) if use_claude and claude_api_key else None
    
    pockets = ["management","labor","evaluacion_experimental",
               "desigualdad","policy","human_machine_interaction","innovacion_difusion"]
    if pocket_filter:
        pockets = [p for p in pockets if p in pocket_filter]
    
    stats = {"unpaywall": 0, "credentials": 0, "claude": 0, "failed": 0}
    
    for pocket in pockets:
        f = f"data/{pocket}_papers_enriched.json"
        with open(f) as fp:
            papers = json.load(fp)
        
        changed = False
        logger.info(f"\n{'='*50}\n🔍 {pocket}\n{'='*50}")
        
        for i, paper in enumerate(papers):
            if paper.get("abstract"):
                continue
            
            url = paper.get("url","") or paper.get("scholar_link","")
            title = paper.get("title","")
            if not url:
                stats["failed"] += 1
                continue
            
            abstract = None
            method = None
            
            # Skip books/proquest
            if any(x in url for x in ["books.google","proquest","google.com/books"]):
                stats["failed"] += 1
                continue
            
            # Strategy 1: Unpaywall via DOI
            doi = paper.get("doi") or get_doi_from_url(url)
            if doi:
                abstract = unpaywall_fetch(doi)
                if abstract:
                    method = "unpaywall"
                    paper["doi"] = paper.get("doi") or doi
                time.sleep(0.3)
            
            # Strategy 2: Institutional credentials
            if not abstract and use_credentials and username:
                abstract = with_credentials(url, username, password)
                if abstract: method = "credentials"
                time.sleep(0.5)
            
            # Strategy 3: Claude API
            if not abstract and claude_client:
                abstract = claude_extract(url, title, claude_client)
                if abstract: method = "claude"
                time.sleep(0.3)
            
            if abstract:
                paper["abstract"] = abstract
                stats[method] += 1
                changed = True
                logger.info(f"  [{i+1}] ✅ [{method}] {title[:60]}...")
            else:
                stats["failed"] += 1
                logger.info(f"  [{i+1}] ❌ {title[:60]}...")
        
        if changed:
            with open(f, "w") as fp:
                json.dump(papers, fp, indent=2, ensure_ascii=False)
    
    logger.info(f"\n📊 Results: Unpaywall={stats['unpaywall']} | Credentials={stats['credentials']} | Claude={stats['claude']} | Failed={stats['failed']}")
    return stats

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", action="store_true")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--claude", action="store_true")
    parser.add_argument("--claude-key", default=os.getenv("ANTHROPIC_API_KEY",""))
    parser.add_argument("--pocket", nargs="+")
    args = parser.parse_args()
    
    run(
        use_credentials=args.credentials,
        username=args.username,
        password=args.password,
        use_claude=args.claude,
        claude_api_key=args.claude_key,
        pocket_filter=args.pocket
    )
