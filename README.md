# 📚 Literatura Review Pipeline - BID-IA Project

**Complete Literature Review System** with AI-powered paper analysis, semantic networks, and interactive dashboards.

**Status**: ✅ Production Ready | **Papers**: 49 | **Pockets**: 7 | **Connections**: 1,176

---

## 🚀 Quick Start (60 seconds)

```bash
# 1. Go to project directory
cd /Users/mariaamontoya/literatura-review-phase1

# 2. Run quick start (automatically starts server + opens dashboard)
bash QUICK_START.sh

# OR manual 3-step start:
# pip install -r scripts/requirements.txt
# python -m http.server 8000
# Open: http://localhost:8000/outputs/dashboard_consolidated.html
```

**Result**: Dashboard opens automatically at `http://localhost:8000/outputs/dashboard_consolidated.html`

---

## 📊 What You Get

### Dashboard Features
- **49 Papers** across 7 thematic pockets
- **Interactive Network** visualization (49 nodes, 1,176 semantic connections)
- **Real-time Filters** (pocket, status, minimum score)
- **6 Tabs**: Overview, Pockets, Network, Analysis, Gaps, Data
- **Downloadable JSON** files for all papers and network data

### Architecture
```
49 Papers → Reviewer (score) → Synthesizer (insights) → Mapper (network) → Dashboard
```

---

## 🎯 The 7 Pockets

| Pocket | Papers | Quality | Avg Score |
|--------|--------|---------|-----------|
| **Management** | 7 | ✅ Excellent | 8.6/10 |
| **Evaluación Experimental** | 7 | ✅ Excellent | 8.0/10 |
| **HMI** | 7 | ✅ Good | 6.8/10 |
| **Innovación y Difusión** | 7 | ✅ Good | 6.5/10 |
| **Labor Markets** | 7 | ⚠️ Mixed | 6.6/10 |
| **Policy** | 7 | ⚠️ Mixed | 5.7/10 |
| **Desigualdad** | 7 | 🔴 Needs Work | 5.4/10 |

**Acceptance**: 32/49 = 65% (score ≥6/10)

---

## 🎨 Main Dashboard

```
http://localhost:8000/outputs/dashboard_consolidated.html

Features:
├── Overview       → 49 papers, status metrics
├── Pockets        → Per-pocket statistics
├── Network        → Interactive 49-node graph (1,176 edges)
├── Analysis       → 4 distribution charts
├── Gaps           → Coverage gaps identified
└── Data           → Download all JSON files
```

---

## 📁 Project Structure

```
literatura-review-phase1/
├── 🚀 QUICK_START.sh           ← Start here!
├── README.md                   ← You are here
├── START_HERE.md               ← User guide
├── DEPLOYMENT.md               ← Technical setup
│
├── 📊 outputs/
│   ├── dashboard_consolidated.html   ← MAIN
│   └── dashboard_v3.html
│
├── 📈 data/
│   ├── consolidated_graph.json       (340 KB)
│   ├── [pocket]_reviewed.json        (7 files)
│   ├── [pocket]_synthesized.json     (7 files)
│   └── [pocket]_papers.json          (7 files)
│
└── 🐍 scripts/
    ├── pipeline_orchestrator.py
    ├── reviewer.py
    ├── synthesizer.py
    ├── mapper.py
    └── requirements.txt
```

---

## 🔧 Requirements

- Python 3.8+
- 50 MB disk space
- Port 8000 available
- Modern browser

---

## 📖 Key Docs

| File | Purpose |
|------|---------|
| **README.md** | Overview (you are here) |
| **START_HERE.md** | Quick navigation guide |
| **DEPLOYMENT.md** | Technical setup & troubleshooting |
| **CLAUDE.md** | Project architecture |
| **PIPELINE_RESULTS.md** | Detailed results report |

---

## 🎉 Ready?

```bash
bash QUICK_START.sh
```

Dashboard opens at: `http://localhost:8000/outputs/dashboard_consolidated.html`

---

### More Info
- Full guide: START_HERE.md
- Technical: DEPLOYMENT.md
- Architecture: CLAUDE.md

**Status**: ✅ Production Ready - Enjoy! 🚀
