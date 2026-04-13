# Literatura Review Phase 1

Automated, systematic review of **top-tier global literature** on AI adoption and productivity in Colombia/LatAm context.

---

## 📁 Project Structure

```
literatura-review-phase1/
├── CLAUDE.md                      # Main project spec
├── RESEARCHER.md                  # Search strategy
├── REVIEWER.md                    # Evaluation rubric
├── SYNTHESIZER.md                 # Metadata extraction
├── MAPPER.md                      # Graph construction
├── UI.md                          # Dashboard specification
├── README.md                      # This file
├── .env.example                   # API keys template
├── scripts/
│   ├── researcher.py
│   ├── reviewer.py
│   ├── synthesizer.py
│   ├── mapper.py
│   ├── ui.py
│   └── requirements.txt
├── data/
│   ├── raw_papers.csv
│   ├── reviewed_papers.json
│   ├── synthesized_papers.json
│   └── graph.json
└── outputs/
    ├── visualization.html
    ├── gaps_report.md
    └── logs/
```

---

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install -r scripts/requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your API credentials
```

### 3. Run Pipeline
```bash
cd scripts
python researcher.py      # Collect papers
python reviewer.py        # Apply rubric
python synthesizer.py     # Extract insights
python mapper.py          # Build graph
streamlit run ui.py       # Open dashboard
```

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Main specification
- **[RESEARCHER.md](RESEARCHER.md)** - Search strategy
- **[REVIEWER.md](REVIEWER.md)** - Evaluation rubric
- **[SYNTHESIZER.md](SYNTHESIZER.md)** - Data schema
- **[MAPPER.md](MAPPER.md)** - Graph construction
- **[UI.md](UI.md)** - Dashboard spec

---

**Status**: Phase 1 Complete. Ready for Phase 2 (Prototipo).
