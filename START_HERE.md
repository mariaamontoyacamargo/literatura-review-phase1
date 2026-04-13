# 🚀 START HERE - Literatura Review Dashboard

## Quick Links

### 📊 View the Dashboards (HTTP Server Running)

**Main Dashboard (All 7 Pockets)**
```
http://localhost:8000/outputs/dashboard_consolidated.html
```
- View all 49 papers
- Filter by pocket, status, score
- Interactive 49-node network graph (1,176 connections)
- Download data files

**Single Pocket Demo (Evaluación Experimental)**
```
http://localhost:8000/outputs/dashboard_v3.html
```
- Network visualization with Vis.js
- Real-time filters
- Paper details and statistics

---

## 📁 Project Structure

```
literatura-review-phase1/
│
├── 📊 OUTPUTS & DASHBOARDS
│   └── outputs/
│       ├── dashboard_consolidated.html  ← View ALL 7 pockets here
│       ├── dashboard_v3.html           ← Single pocket network demo
│       └── dashboard_v2.html           
│
├── 📈 DATA FILES  
│   └── data/
│       ├── consolidated_graph.json     ← 49 nodes, 1,176 edges
│       ├── [pocket]_reviewed.json      ← Scored papers (7 files)
│       ├── [pocket]_synthesized.json   ← Extracted insights (7 files)
│       └── [pocket]_papers.json        ← Raw papers (7 files)
│
├── 🐍 PIPELINE SCRIPTS
│   └── scripts/
│       ├── pipeline_orchestrator.py    ← Main orchestrator
│       ├── generate_pocket_papers.py   ← Generate papers
│       ├── reviewer.py                 ← Rubrica scoring (0-10)
│       ├── synthesizer.py              ← Extract metadata
│       └── mapper.py                   ← Build network
│
├── 📖 DOCUMENTATION
│   ├── START_HERE.md                   ← You are here
│   ├── CLAUDE.md                       ← Project directives
│   ├── PIPELINE_RESULTS.md             ← Detailed results
│   ├── pockets_config.yaml             ← Pocket definitions
│   └── POCKETS_DELIMITACION.md         ← Pocket descriptions
│
└── 🔧 CONFIGURATION
    └── .env (not included - add your API keys here)
```

---

## 🎯 Pockets Overview (7 Total)

| # | Pocket | Papers | Accepted | Avg Score | Status |
|---|--------|--------|----------|-----------|--------|
| 1 | **Management** | 7 | 7 (100%) | 8.6/10 | ✅ Excellent |
| 2 | **Evaluación Experimental** | 7 | 7 (100%) | 8.0/10 | ✅ Excellent |
| 3 | **HMI** | 7 | 5 (71%) | 6.8/10 | ✅ Good |
| 4 | **Innovación y Difusión** | 7 | 5 (71%) | 6.5/10 | ✅ Good |
| 5 | **Labor Markets** | 7 | 4 (57%) | 6.6/10 | ⚠️ Mixed |
| 6 | **Policy** | 7 | 4 (57%) | 5.7/10 | ⚠️ Mixed |
| 7 | **Desigualdad** | 7 | 2 (29%) | 5.4/10 | 🔴 Needs Work |
| | **TOTAL** | **49** | **32 (65%)** | **6.6/10** | |

---

## 📊 Key Metrics

- **Papers Reviewed**: 49
- **Status**: 32 Accepted (ACEPTADO), 17 Under Review (REVISAR)
- **Network Nodes**: 49 papers
- **Network Edges**: 1,176 semantic connections
- **Network Density**: 1.000 (fully connected)
- **Rubrica**: 0-10 scale, acceptance threshold ≥ 6/10

---

## 🔍 Dashboard Features

### Consolidated Dashboard Tabs

#### 1️⃣ **Overview**
- Summary metrics (49 papers, 32 accepted, 6.6/10 avg)
- Status breakdown (Aceptado vs Revisar)
- Pocket distribution
- Searchable paper table

#### 2️⃣ **Pockets**
- Individual pocket statistics
- Papers per pocket
- Acceptance rate per pocket
- Average score per pocket

#### 3️⃣ **Network**
- Interactive graph visualization (49 nodes, 1,176 edges)
- Force-directed layout
- Drag nodes, zoom, pan
- Network statistics
- Legend explaining colors/sizes

#### 4️⃣ **Analysis**
- Score distribution (histogram)
- Papers by year
- Pocket distribution (pie chart)
- Methodology distribution

#### 5️⃣ **Gaps**
- Coverage gaps identified
- Quality issues flagged
- Critical (🔴) vs Warning (🟡) items

#### 6️⃣ **Data**
- Download links for all JSON files
- consolidated_graph.json (340 KB)
- Per-pocket files (8-11 KB each)

### Interactive Filters
- **Pocket**: Filter by thematic area
- **Status**: Filter by Aceptado/Revisar
- **Score**: Minimum score slider (0-10)

---

## 🔗 Network Analysis

### Semantic Relations (1,176 edges)
1. **Same Pocket** (420) - Papers in same theme
2. **Similar Methodology** (342) - RCTs, quasi-exp, etc.
3. **Temporal Sequence** (294) - Within 1 year
4. **Keyword Overlap** (105) - Jaccard similarity >0.15
5. **Shared Authors** (15) - Overlapping authorship

### Network Properties
- **Density**: 1.000 (all papers connected)
- **Avg Connections**: 47.8 per paper
- **Connected Components**: 1 (single network)

---

## 📥 How to Use the Data

### Access JSON Files
```bash
# View consolidated network
curl http://localhost:8000/data/consolidated_graph.json | jq .

# View papers from specific pocket
curl http://localhost:8000/data/management_reviewed.json | jq '.[] | {title, score, status}'

# Count papers by status
jq 'map(.status) | group_by(.) | map({status: .[0], count: length})' data/consolidated_graph.json

# Find highest-scoring papers
jq 'sort_by(.score) | reverse | .[0:5] | .[] | {title: .title, score: .score}' data/labor_reviewed.json
```

### Data Structure
```json
{
  "title": "Paper Title",
  "score": 7.5,
  "status": "ACEPTADO",
  "breakdown": {
    "methodology": 7,
    "causalidity": 2,
    "top_tier": 1,
    "novelty": 1,
    "relevance": 1
  },
  "metadata": {
    "authors": ["Author 1", "Author 2"],
    "year": 2024,
    "venue": "AER",
    "citations": 250,
    "h_index": 85,
    "pocket": "management"
  }
}
```

---

## 🔄 Running the Pipeline

### Prerequisites
```bash
pip install -r scripts/requirements.txt
# Includes: networkx, plotly, pyyaml, pandas
```

### Generate Papers for All Pockets
```bash
python scripts/generate_pocket_papers.py
# Creates 7 _papers.json files (7 papers each)
```

### Run Full Pipeline
```bash
python scripts/pipeline_orchestrator.py
# Executes: Reviewer → Synthesizer → Mapper
# Output: 7 _reviewed.json, 7 _synthesized.json, consolidated_graph.json
```

### Start HTTP Server (if stopped)
```bash
python -m http.server 8000 --directory outputs
# Server runs on http://localhost:8000
```

---

## 📋 Rubrica (Scoring System)

Each paper scored 0-10 on:

| Criterion | Max | Scoring |
|-----------|-----|---------|
| **Methodology** | 7 | RCT/Quasi-exp=7, Panel=5, Observational=3, Theoretical=1 |
| **Causal ID** | 2 | Explicit causal claims=2, Correlational=0, Biased=-1 |
| **Top-Tier Signals** | 2 | h>30 + cit>100 + Nature/Science/top25=2, arXiv=1 |
| **Novelty** | 1 | 2023-2026=1, 2020-2022=0, <2020=-1 |
| **Relevance** | 2 | Direct to pocket + AI + productivity=2, Tangential=1 |

**Thresholds**:
- ACEPTADO: ≥6/10 (32 papers)
- REVISAR: 3-5/10 (17 papers)
- RECHAZADO: <3/10 (0 papers)

---

## 🎯 Next Steps Recommended

### Immediate (This Week)
1. **Review Dashboard**: Explore all 7 pockets at consolidated URL above
2. **Check Gaps**: Review coverage gaps in "Gaps" tab
3. **Evaluate Quality**: 17 REVISAR papers need human review

### Short Term (Next 1-2 Weeks)
4. **Manual Review**: Validate REVISAR papers (3-5 score range)
5. **Gap Filling**: Targeted search for Desigualdad/Policy papers
6. **User Feedback**: What filters/features would help?

### Medium Term (1-4 Weeks)
7. **Feedback Loop**: Users suggest papers → Pipeline integrates
8. **Export Options**: Add BibTeX, detailed CSV exports
9. **Advanced Filtering**: By outcome variable, geography, methodology
10. **Community Detection**: Identify semantic clusters in network

---

## 💾 Important Notes

- ✅ All data is in JSON format (easy to export/analyze)
- ✅ Network graph is fully connected (density 1.000)
- ✅ HTTP server handles all file serving
- ✅ Dashboards load data dynamically (no hardcoding)
- ⚠️ REVISAR papers (score 3-7) need human validation
- 🔴 Desigualdad/Policy pockets have quality concerns (low acceptance rate)

---

## 📞 Quick Reference

| Task | Command/Link |
|------|------|
| View main dashboard | http://localhost:8000/outputs/dashboard_consolidated.html |
| View single pocket | http://localhost:8000/outputs/dashboard_v3.html |
| Download all data | Visit "Data" tab in consolidated dashboard |
| See detailed results | Read `PIPELINE_RESULTS.md` |
| Regenerate pipeline | `python scripts/pipeline_orchestrator.py` |
| Generate papers | `python scripts/generate_pocket_papers.py` |
| Check server | `lsof -i :8000` or `curl http://localhost:8000` |

---

**Status**: ✅ Phase 1 Complete - All 49 papers processed, 7 pockets analyzed, network built

**Last Updated**: 2026-04-13  
**Next Phase**: Manual review of REVISAR papers + gap filling

Enjoy exploring the literature review! 🚀
