# BID-IA Literature Review Agent

**Un agente CLI con Claude que orquesta todo el pipeline de revisión de literatura.**

---

## Cómo funciona

```
Tu tarea en lenguaje natural
        ↓
   Claude (Sonnet)       ← tiene 7 tools disponibles
        ↓
  decide qué hacer       ← genera queries, decide qué buscar, qué revisar
        ↓
  ejecuta tools          ← search_papers, review_papers_with_ai, save_papers, etc.
        ↓
  Claude revisa          ← lee abstracts y aplica rúbrica con juicio real (Haiku)
        ↓
  guarda resultados      ← data/{pocket}_reviewed_enriched.json
        ↓
  reporta qué encontró   ← gaps, aceptados, rechazados
```

**Diferencia clave vs el pipeline anterior:**
- Antes: el "review" era matching de keywords (frágil, muchos falsos positivos)
- Ahora: Claude lee el abstract y decide con juicio académico real

---

## Setup

```bash
# Instalar dependencias (ya instaladas si usas el venv del proyecto)
pip install anthropic requests

# Configurar API key
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Comandos principales

### Ver estado del corpus
```bash
python scripts/agent.py --status
```
No requiere API key. Muestra cuántos papers hay por pocket, cuántos aceptados, y % del goal.

### Pipeline completo para un pocket
```bash
python scripts/agent.py --pocket labor
python scripts/agent.py --pocket evaluacion_experimental
python scripts/agent.py --pocket desigualdad
```
Hace todo: check status → busca papers → revisa → sintetiza → guarda.

### Solo una etapa del pipeline
```bash
python scripts/agent.py --pocket labor --mode search      # solo buscar
python scripts/agent.py --pocket labor --mode review      # solo revisar pendientes
python scripts/agent.py --pocket labor --mode synthesize  # solo sintetizar aceptados
```

### Tareas en lenguaje natural
```bash
python scripts/agent.py "¿qué gaps hay en el corpus actual?"
python scripts/agent.py "busca los papers de Brynjolfsson, Dell'Acqua y Noy & Zhang"
python scripts/agent.py "revisa los 20 papers con más citas del pocket HMI"
python scripts/agent.py "¿cuántos papers tenemos sobre LATAM o Colombia?"
```

### Modo interactivo
```bash
python scripts/agent.py --interactive
```

---

## Las 7 tools disponibles para Claude

| Tool | Qué hace | Quién la ejecuta |
|------|----------|-----------------|
| `get_corpus_status` | Estado actual de todos los pockets | Python (determinista) |
| `get_pocket_definition` | Pregunta central, criterios, señales de calidad | Python (determinista) |
| `search_papers` | Busca en Semantic Scholar o NBER | Python → API externa |
| `load_papers` | Carga papers existentes de un pocket | Python (determinista) |
| `review_papers_with_ai` | **Claude Haiku revisa papers con la rúbrica** | Claude Haiku (IA) |
| `synthesize_papers` | **Claude Haiku extrae insights estructurados** | Claude Haiku (IA) |
| `save_papers` | Guarda papers al archivo del pocket | Python (determinista) |

---

## Rúbrica de evaluación (aplicada por Claude)

| Criterio | Escala | Notas |
|----------|--------|-------|
| Metodología | 0-4 | 4=RCT/cuasi-exp, 3=panel/FE, 2=framework, 1=descriptivo, 0=teoría pura |
| Causalidad | 0-2 | 2=IV/RCT/DiD explícito, 1=correlación fuerte, 0=sin evidencia |
| Top-tier | 0-2 | 2=venue top o autor referente, 1=arXiv/WP sólido, 0=desconocido |
| Novedad | -1/0/1 | 1=2022-2026, 0=2020-2021, -1=pre-2020 |
| Relevancia | 0-2 | 2=responde la pregunta central del pocket, 1=contexto, 0=no relevante |

**Umbrales:**
- `ACEPTADO`: score ≥ 7, O (score ≥ 5 AND relevancia=2 AND ≥3 criterios del pocket)
- `REVISAR`: score 3-6
- `RECHAZADO`: score < 3 O relevancia = 0

---

## Output generado

```
data/
  {pocket}_reviewed_enriched.json    ← papers con score, status, breakdown, criteria, synthesis
outputs/
  review_interface.html              ← UI manual para override de decisiones
  bid_dashboard.html                 ← dashboard cliente BID con red de literatura
```

Para regenerar los dashboards después de correr el agente:
```bash
python scripts/generate_review_interface.py
python scripts/generate_pocket_dashboard.py   # (si existe)
```

---

## Costos estimados

| Tarea | Modelo | Costo aprox. |
|-------|--------|-------------|
| Orquestación (Sonnet) | claude-sonnet-4-6 | ~$0.01-0.05 por tarea |
| Review de 30 papers (Haiku) | claude-haiku-4-5 | ~$0.002-0.01 |
| Síntesis de 20 papers (Haiku) | claude-haiku-4-5 | ~$0.002-0.01 |
| Pipeline completo 1 pocket | Sonnet + Haiku | ~$0.05-0.15 |
| Pipeline 7 pockets | Sonnet + Haiku | ~$0.35-1.00 |

---

## Flujo de trabajo recomendado

```bash
# 1. Ver dónde estamos
python scripts/agent.py --status

# 2. Correr un pocket a la vez (empieza por los de alta prioridad)
python scripts/agent.py --pocket evaluacion_experimental
python scripts/agent.py --pocket labor
python scripts/agent.py --pocket desigualdad

# 3. Revisar manualmente los casos borde
open http://localhost:8000/outputs/review_interface.html

# 4. Regenerar dashboards
python scripts/generate_review_interface.py

# 5. Ver el producto al cliente
open http://localhost:8000/outputs/bid_dashboard.html
```