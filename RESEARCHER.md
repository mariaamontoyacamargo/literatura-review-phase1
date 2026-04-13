# RESEARCHER.md - Estrategia de Búsqueda Global TOP-TIER

## Objetivo
Recolectar papers TOP-TIER globales sobre adopción de IA y productividad, filtrados por venue, citaciones, h-index de autores, y validados con signals de Twitter/X.

---

## Pockets Temáticos (Ejes de Búsqueda)

### 1. **AI Adoption at Firm Level**
- Queries: `"AI adoption firm productivity papers 2023-2026"`, `"enterprise AI implementation impact on productivity"`
- Target: 5-10 papers mínimo
- Métricas clave: firm-level productivity, revenue, TFP

### 2. **AI Adoption at Worker Level**
- Queries: `"generative AI worker productivity RCTs 2024-2026"`, `"AI tools impact on individual worker output"`
- Target: 5-10 papers mínimo
- Métricas clave: task completion time, quality, error rates

### 3. **AI Adoption at Team Level**
- Queries: `"AI collaboration team productivity"`, `"generative AI impact on team collaboration"`
- Target: 5-10 papers mínimo
- Métricas clave: team output, coordination efficiency, innovation

### 4. **AI Adoption at Task Level**
- Queries: `"generative AI task productivity 2024-2026"`, `"AI automation specific tasks productivity gains"`
- Target: 5-10 papers mínimo
- Métricas clave: task speedup, error reduction, scalability

---

## Filtros TOP-TIER

Cada paper recolectado DEBE cumplir MÍNIMO 3 de estos:

- ✅ **Venue**: Nature, Science, top 25 CS/econ venues (arXiv preprints OK si recent 2025-2026)
- ✅ **Author h-index**: >20 (preferible >30)
- ✅ **Citation count**: >50 (preferible >100)
- ✅ **Year**: 2023-2026 (recency bias favorable)
- ✅ **Methodology**: RCT, quasi-experimental, panel data con identificación causal
- ✅ **Empirical vs theoretical**: Prioritize empirical (papers with data)

---

## Fuentes API

### 1. **SerpAPI + Google Scholar**
- Query: `site:scholar.google.com "{query}" 2023-2026`
- Extrae: título, autores, año, citaciones, venue
- Rate limit: 100 requests/month (plan free)

### 2. **Arxiv API**
- Queries: `cat:cs.CY OR cat:econ.EM AND ("AI" OR "generative" OR "LLM" OR "productivity")`
- Extrae: abstract, autores, versiones, citaciones
- Rate limit: generous (unlimited si respecta delay ~3s entre requests)

### 3. **Twitter/X Signals**
- Tweepy API: busca tweets que citen papers tops
- **Uso**: Valida impacto percibido en industry
- **Filtro**: Manual verify que cite paper, no trending topic genérico

---

**Última actualización**: 2026-04-13  
**Status**: Listo para scripting
