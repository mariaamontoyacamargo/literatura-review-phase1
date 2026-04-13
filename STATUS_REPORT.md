# 📊 LITERATURA REVIEW - Status Report (2026-04-13)

## Executive Summary

✅ **Phase 1 UPGRADED: Real Papers + Research Integration**

- **Old**: 49 synthetic papers (generated, not real)
- **New**: 104 real papers from ArXiv API
- **Next**: Expand to 300+ papers from multiple sources

---

## What Changed

### Before (Synthetic)
```
generate_pocket_papers.py
    ↓ (generates fake papers)
    49 papers with made-up metadata
    ↓
pipeline_orchestrator.py
    ↓ (reviewer, synthesizer, mapper)
    49 nodes, 1,176 edges
    ↓ 
dashboard_consolidated.html (49 papers)
```

### After (Real Papers from ArXiv)
```
researcher_arxiv.py
    ↓ (searches ArXiv API)
    104 REAL papers from academic sources
    (+ title, authors, abstract, link, year)
    ↓
pipeline_orchestrator.py
    ↓ (reviewer, synthesizer, mapper)
    26 nodes, 342 edges
    ↓
dashboard_consolidated.html (104 real papers)
```

---

## Current Data

### Papers by Pocket (REAL from ArXiv)

| Pocket | Count | ACEPTADO | Score | Remarks |
|--------|-------|----------|-------|---------|
| Evaluación Experimental | 15 | 1 | 4.1/10 | RCTs, causal methods |
| Innovación y Difusión | 19 | 1 | 4.1/10 | Adoption, S-curves |
| Labor Markets | 15 | 1 | 4.0/10 | Employment, wages |
| Management | 15 | 1 | 4.1/10 | Org adoption, strategy |
| HMI | 13 | 1 | 4.1/10 | UI/UX, interaction |
| Desigualdad | 14 | 1 | 4.1/10 | Inequality, access |
| Policy | 13 | 1 | 4.1/10 | Regulation, governance |
| **TOTAL** | **104** | **7** | **4.1/10** | Real academic papers |

### Network Properties

- **Nodes**: 26 (papers with score ≥ 4.1/10 mostly)
- **Edges**: 342 semantic connections
- **Density**: 1.052 (highly interconnected)
- **Components**: 1 (single connected network)

---

## Limitations (And How to Fix)

### Issue 1: Low Acceptance Rate (7%)

**Why**: Rubrica is too strict for real preprints

**Solution**: 
```python
# CURRENT (strict):
- RCT only → 7 points
- Else → 1-3 points

# IMPROVED (nuanced):
- RCT, quasi-exp, empirical → 5-7 points
- Observational + controls → 3-4 points
- Anything with data → min 2 points
```

**Impact**: 30-40% ACEPTADO rate (more reasonable)

### Issue 2: Only 104 Papers

**Why**: Only searched ArXiv (1 source)

**Solution**: Add:
- Google Scholar (+150 papers, public search)
- NBER working papers (+50 papers, econ focus)
- SSRN preprints (+100 papers, newest work)

**Impact**: 300-400 papers total

### Issue 3: No Link to Original Papers

**Fix**: Dashboard should show:
- ArXiv ID (clickable link)
- Direct PDF link
- Author list
- Publication date
- Abstract excerpt

---

## Files to Know

### Research Layer
```
scripts/researcher_arxiv.py        ✅ DONE (ArXiv search)
scripts/researcher_scholar.py      ⏳ TODO (Google Scholar)
scripts/researcher_nber.py         ⏳ TODO (NBER working papers)
scripts/researcher_ssrn.py         ⏳ TODO (SSRN preprints)
```

### Review Layer
```
scripts/reviewer.py                ⚠️ NEEDS FIX (too strict)
  → Adjust thresholds for real papers
  → Better methodology detection heuristics
```

### Pipeline
```
scripts/pipeline_orchestrator.py   ✅ WORKS (fully automated)
scripts/synthesizer.py             ✅ WORKS
scripts/mapper.py                  ✅ WORKS
```

### Output
```
data/consolidated_graph.json       ✅ UPDATED (104 papers)
data/*_papers_real.json            ✅ NEW (raw ArXiv papers)
outputs/dashboard_consolidated.html ✅ UPDATED (reflects new data)
```

---

## How to Use

### View Current Results
```bash
# Server should be running on port 8000
open http://localhost:8000/outputs/dashboard_consolidated.html
```

### Run Updated Pipeline
```bash
# Papers already in data/*_papers.json (replaced with real)
python scripts/pipeline_orchestrator.py
```

### Expand Search
See `RESEARCHER_GUIDE.md` for:
- How to add more sources
- How to improve rubrica
- How to handle 300+ papers
- Integration templates

---

## Next Steps (In Priority Order)

### SHORT TERM (This week)
1. **Fix Rubrica**: Improve reviewer.py thresholds (30 min)
   - Better acceptance rate for real papers
   - More nuanced methodology detection

2. **Add Links to Dashboard** (1 hour)
   - Show arXiv IDs clickable
   - Show paper abstracts
   - Direct links to PDFs

### MEDIUM TERM (Next 1-2 weeks)
3. **Add Google Scholar** (2-3 hours)
   - 150+ additional papers
   - Fill gaps in coverage
   - See RESEARCHER_GUIDE.md for template

4. **Add NBER + SSRN** (3-4 hours)
   - 150+ additional papers
   - Better econ/policy coverage
   - Pre-publication work

5. **Improve Synthesizer** (2-3 hours)
   - Extract keywords from abstracts
   - Identify outcome variables
   - Better relation detection

### LONG TERM (1-2 months)
6. **Community Detection**: Find clusters in papers
7. **Export Formats**: BibTeX, CSV, RDF
8. **Feedback Loop**: Users suggest papers → Auto-integrate
9. **Real-time Updates**: Check new arXiv papers weekly

---

## Commands Reference

```bash
# Current state (104 papers)
python scripts/researcher_arxiv.py    # Search ArXiv (5 min)
python scripts/pipeline_orchestrator.py # Review+Synthesize+Map (5 sec)

# View results
open http://localhost:8000/outputs/dashboard_consolidated.html

# Backup old data
ls data/backup_synthetic/             # Old 49 papers stored here

# Expand search (when ready)
# python scripts/researcher_scholar.py
# python scripts/researcher_nber.py
# python scripts/researcher_integrated.py
```

---

## Summary

| Metric | Before | After | Goal |
|--------|--------|-------|------|
| Papers | 49 (fake) | 104 (real) | 300+ |
| Sources | 1 (generated) | 1 (ArXiv) | 4+ |
| Acceptance | 65% | 7% | 30% |
| Network | 49 nodes | 26 nodes | 100+ |
| Real links? | No | Yes | Yes |
| Authors? | Fake | Real | Real |
| Abstracts? | Fake | Real | Real |

---

**Key Achievement**: ✅ Workflow now uses REAL papers from ArXiv API  
**Key Limitation**: Rubrica too strict + only 1 source  
**Next Win**: Fix rubrica + add 1 more source = 200+ papers, 30%+ acceptance  

Ready to expand! 🚀
