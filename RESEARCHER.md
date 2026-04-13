# RESEARCHER.md - Estrategia de Búsqueda Global TOP-TIER

## Objetivo
Recolectar papers TOP-TIER globales sobre adopción de IA y productividad, filtrados por venue, citaciones, h-index de autores, y validados con signals de Twitter/X.

---

## Pockets Temáticos (Ejes de Búsqueda) - 7 Temas Principales

### 1. **Evaluación Experimental**
- Queries: `"generative AI RCT experiment 2024-2026"`, `"AI randomized controlled trial productivity"`
- Target: 5-10 papers mínimo
- Métricas clave: metodología RCT, quasi-experimental, field experiments, causal identification

### 2. **Human-Machine Interaction (HMI)**
- Queries: `"human AI interaction design"`, `"AI collaboration human workers"`, `"user experience generative AI"`
- Target: 5-10 papers mínimo
- Métricas clave: interaction patterns, user behavior, adoption barriers, interface design

### 3. **Innovación y Difusión**
- Queries: `"AI innovation adoption diffusion"`, `"generative AI technology diffusion firms"`, `"AI adoption barriers"`
- Target: 5-10 papers mínimo
- Métricas clave: adoption rates, diffusion curves, innovation cycles, technological spillovers

### 4. **Labor Markets (Labor)**
- Queries: `"AI impact labor markets employment"`, `"generative AI job displacement automation"`, `"worker reskilling AI"`
- Target: 5-10 papers mínimo
- Métricas clave: employment effects, wage impacts, skill requirements, labor demand

### 5. **Desigualdad**
- Queries: `"AI inequality wage gaps"`, `"generative AI income distribution"`, `"AI skill premium labor"`, `"AI digital divide"`
- Target: 5-10 papers mínimo
- Métricas clave: inequality metrics, skill distribution, gender gaps, regional disparities

### 6. **Policy**
- Queries: `"AI policy regulation governance"`, `"generative AI policy frameworks"`, `"AI labor policy"`, `"data privacy AI"`
- Target: 5-10 papers mínimo
- Métricas clave: policy recommendations, regulatory frameworks, international comparisons

### 7. **Management**
- Queries: `"AI organizational adoption management"`, `"generative AI firm strategy"`, `"AI implementation organizational change"`
- Target: 5-10 papers mínimo
- Métricas clave: organizational strategy, change management, firm structure, business models

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
