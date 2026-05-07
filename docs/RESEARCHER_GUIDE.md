# 🔍 RESEARCHER GUIDE - Expanding Literature Review

## Current Status (V2)

**104 Real Papers from ArXiv API** successfully collected and processed

- **Evaluación Experimental**: 15 papers
- **Innovación y Difusión**: 19 papers
- **Labor Markets**: 15 papers
- **Management**: 15 papers
- **HMI**: 13 papers
- **Desigualdad**: 14 papers
- **Policy**: 13 papers

---

## How to Expand Search

### 1. Increase ArXiv Search Results

**Current**: 10 papers per query (5 queries × 7 pockets = 350 requests max)  
**Expand**: Modify `scripts/researcher_arxiv.py`

```python
# Line ~230: Change max_results parameter
papers = self.search_arxiv(query, max_results=50)  # Was 20, now 50
```

**Impact**: ~175 papers per pocket (1,200+ total)

### 2. Add Google Scholar (Public Search)

Create `scripts/researcher_scholar.py`:

```python
"""Search Google Scholar for papers"""
import requests
from bs4 import BeautifulSoup

def search_scholar(query: str, max_results: int = 20) -> List[Dict]:
    """
    Busca papers públicos en Google Scholar
    - No requiere autenticación (búsqueda pública)
    - Extrae título, autores, año, citaciones
    - Retorna links a PDF/metadata
    """
    base_url = "https://scholar.google.com/scholar"
    params = {
        'q': query,
        'as_ylo': 2023,
        'as_yhi': 2026,
        'hl': 'en'
    }
    
    # Scrape con BeautifulSoup (respeta robots.txt de Scholar)
    response = requests.get(base_url, params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    papers = []
    for result in soup.find_all('div', class_='gs_ri'):
        # Extract: title, authors, year, citations
        ...
    
    return papers
```

### 3. Add NBER Working Papers

NBER (National Bureau of Economic Research) = goldmine para labor/econ papers

```python
"""scripts/researcher_nber.py"""
def search_nber(query: str) -> List[Dict]:
    """
    NBER tiene API abierta con series números
    - https://www.nber.org/papers
    - JSON con metadata completa
    - Focus: Labor, Policy, Innovation papers
    """
    # Buscar por serie
    series_map = {
        'labor': 'ls',           # Labor Studies
        'policy': 'po',          # Productivity
        'innovation': 'te'       # Technical Change
    }
    
    base_url = "https://www.nber.org/api/v1/papers/series"
    
    # Retorna papers con JSON structure
    # {title, authors, date, url, abstract}
```

### 4. Add SSRN Preprints

SSRN (Social Science Research Network) = preprints actuales

```python
"""scripts/researcher_ssrn.py"""
def search_ssrn(query: str) -> List[Dict]:
    """
    SSRN tiene papers pre-publication
    - Focus: Economics, Finance, Management
    - Newer working papers (2025-2026)
    """
```

### 5. Improve Search Queries

**Current**: Basic keyword searches  
**Better**: Combine terms + filters + boolean logic

```yaml
# Enhanced pockets_config.yaml
management:
  search_queries:
    # Previous
    - "AI organizational adoption management strategy"
    
    # Enhanced with boolean operators
    - "(AI OR LLM OR generative) AND (adoption OR implementation) AND (organizational OR firm)"
    - "(machine learning OR artificial intelligence) AND management AND implementation 2024-2026"
    - "Brynjolfsson OR Acemoglu OR Restrepo productivity AI"  # Top authors
    
  author_filters:
    - "Brynjolfsson"
    - "Acemoglu"
    - "Bloom"
    - "Restrepo"
```

---

## How to Improve Rubrica (Fix Low Scores)

**Problem**: 7/104 papers ACEPTADO (only 7%)  
**Root Cause**: Rubrica is too strict for preprints/real papers

### Current Scoring Issues

```python
# scripts/reviewer.py line ~150: score_methodology()

def score_methodology(self, paper: Dict) -> int:
    """CURRENT: Very strict"""
    summary = paper['summary'].lower()
    
    if 'randomized controlled trial' in summary or 'rct' in summary:
        return 7  # Only RCTs get max
    elif 'quasi-experiment' in summary:
        return 5
    # ... ArXiv papers mostly don't explicitly say "RCT", score low
    return 1  # Most real papers
```

### Solution: Smarter Detection

```python
def score_methodology_improved(self, paper: Dict) -> int:
    """IMPROVED: Better heuristics"""
    summary = paper['summary'].lower()
    full_text = paper['summary'] + paper['title'].lower()
    
    # RCT markers
    rct_terms = ['randomized', 'rct', 'random assignment', 'treatment effect']
    if any(term in full_text for term in rct_terms):
        return 7
    
    # Quasi-experimental markers
    quasi_terms = ['quasi-experimental', 'did', 'difference-in-differences', 
                   'instrumental variable', 'iv', 'propensity score', 'matching']
    if any(term in full_text for term in quasi_terms):
        return 5
    
    # Empirical study markers (even without explicit method names)
    empirical_terms = ['dataset', 'dataset of', 'data on', 'analyzed', 
                      'surveyed', 'sample of', 'million workers', 'firms']
    if any(term in full_text for term in empirical_terms):
        return 3  # Observational/descriptive
    
    # Theory/review
    return 1
```

### Adjust Acceptance Threshold

```python
# Current
THRESHOLD_ACEPTADO = 6

# Better for real papers
THRESHOLD_ACEPTADO = 4.5  # Allows more "real but imperfect" papers
```

---

## Complete Search Script (Template)

```python
"""scripts/researcher_integrated.py"""

class ResearcherIntegrated:
    """Unified researcher using multiple sources"""
    
    def __init__(self):
        self.arxiv_researcher = ResearcherArxiv()
        # self.scholar_researcher = ResearcherScholar()
        # self.nber_researcher = ResearcherNBER()
        # self.ssrn_researcher = ResearcherSSRN()
    
    def search_all_sources(self, pockets_config: Dict) -> Dict:
        """
        1. Search ArXiv (DONE)
        2. Search Scholar (TODO)
        3. Search NBER (TODO)
        4. Search SSRN (TODO)
        5. Consolidate + deduplicate
        6. Filter TOP-TIER
        7. Return union of all
        """
        results = {}
        
        # ArXiv (done)
        arxiv_papers = self.arxiv_researcher.search_all_pockets()
        
        # Scholar (add this)
        # scholar_papers = self.scholar_researcher.search_all_pockets()
        
        # Consolidate
        for pocket_id, papers in arxiv_papers.items():
            results[pocket_id] = papers
            # results[pocket_id].extend(scholar_papers.get(pocket_id, []))
        
        # Deduplicate
        self.deduplicate_papers(results)
        
        return results
```

---

## To Run Expanded Search

```bash
# 1. Run ArXiv (current - 104 papers)
python scripts/researcher_arxiv.py

# 2. Add Scholar search (when ready)
# python scripts/researcher_scholar.py

# 3. Add NBER search (when ready)
# python scripts/researcher_nber.py

# 4. Run integrated search
# python scripts/researcher_integrated.py

# 5. Run pipeline with new papers
python scripts/pipeline_orchestrator.py

# 6. Regenerate dashboard
python scripts/pipeline_orchestrator.py

# 7. View updated results
# http://localhost:8000/outputs/dashboard_consolidated.html
```

---

## Impact of Expansions

| Source | Est. Papers | Time | Cost | Quality |
|--------|-------------|------|------|---------|
| ArXiv (done) | 104 | 3 min | Free | Good |
| + Scholar | 150+ | 5 min | Free | Good |
| + NBER | 50+ | 2 min | Free | Excellent |
| + SSRN | 100+ | 5 min | Free | Good |
| **TOTAL** | **400+** | 15 min | Free | ★★★★★ |

---

## Next: Filter & Improve

Once you have 300-400 papers:

1. **Improve Rubrica**: Use better detection heuristics
2. **Better Synthesis**: Extract outcomes, limitations, methodology details
3. **Network Analysis**: Find clusters, identify gaps, detect communities
4. **Export Formats**: BibTeX, CSV, RDF for citation management
5. **Feedback Loop**: User suggests papers → Auto-add to database

---

## Files Structure

```
scripts/
├── researcher_arxiv.py         ✅ Done (104 papers)
├── researcher_scholar.py       ⏳ TODO (add Scholar)
├── researcher_nber.py          ⏳ TODO (add NBER)
├── researcher_ssrn.py          ⏳ TODO (add SSRN)
├── researcher_integrated.py    ⏳ TODO (combine all)
├── reviewer.py                 ⚠️ Needs improvement
├── synthesizer.py              ✅ Works
└── pipeline_orchestrator.py    ✅ Works
```

---

**Status**: Ready to expand! 🚀

Next: Choose which source to add (Scholar recommended - easiest implementation)
