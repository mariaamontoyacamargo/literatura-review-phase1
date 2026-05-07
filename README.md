# BID-IA — Revisión de Literatura: Adopción de IA en Firmas

**Fedesarrollo & Banco Interamericano de Desarrollo · Colombia y LATAM · 2026**

> ¿Qué determina si una firma adopta IA efectivamente y captura valor?
> ¿Qué condiciones habilitantes requieren las MiPyMEs de LATAM?

---

## Estructura del proyecto

```
├── AGENT.md                     ← Cómo correr el agente (leer primero)
├── POCKETS_DELIMITACION.md      ← 7 pockets: preguntas, queries, criterios
├── PREGUNTA_ACADEMICA.md        ← Pregunta de investigación central
│
├── scripts/
│   ├── agent.py                 ← Agente principal (entry point)
│   ├── pockets.py               ← Definiciones de pockets (source of truth)
│   ├── generate_review_interface.py
│   ├── generate_pocket_dashboard.py
│   └── archive/                 ← Scripts anteriores (referencia)
│
├── data/
│   ├── {pocket}_reviewed_enriched.json  ← Papers revisados (activos)
│   ├── bid_network.json                  ← Red de literatura
│   └── archive/                          ← Datos intermedios
│
└── outputs/
    ├── review_interface.html    ← Revisión manual (localhost:8000)
    └── bid_dashboard.html       ← Dashboard cliente BID
```

---

## Inicio rápido

```bash
# Setup (solo primera vez)
source venv/bin/activate
export ANTHROPIC_API_KEY=sk-ant-...

# Estado actual del corpus
python scripts/agent.py --status

# Pipeline completo para un pocket
python scripts/agent.py --pocket labor
python scripts/agent.py --pocket evaluacion_experimental

# Solo buscar / solo revisar / solo sintetizar
python scripts/agent.py --pocket labor --mode search
python scripts/agent.py --pocket labor --mode review
python scripts/agent.py --pocket labor --mode synthesize

# Tarea en lenguaje natural
python scripts/agent.py "qué gaps hay en el corpus actual?"

# Revisar manualmente
python -m http.server 8000 &
open http://localhost:8000/outputs/review_interface.html
open http://localhost:8000/outputs/bid_dashboard.html
```

---

## Los 7 pockets temáticos

| # | Pocket | Pregunta central | Prioridad |
|---|--------|-----------------|-----------|
| 1 | Evaluación Experimental | ¿Qué determina resultados causales de adopción IA? | HIGH |
| 2 | Human-Machine Interaction | ¿Cuándo la interacción humano-IA genera o destruye valor? | HIGH |
| 3 | Innovación y Difusión | ¿Cómo se difunde la IA y cuándo se traduce en productividad? | MEDIUM |
| 4 | Labor y Mercado de Trabajo | ¿Cómo redistribuye la adopción el trabajo y valor? | HIGH |
| 5 | Desigualdad | ¿Bajo qué condiciones la adopción amplía o reduce brechas? | HIGH |
| 6 | Management y Organización | ¿Cómo la organización determina adopción y captura de valor? | HIGH |
| 7 | Policy y Gobernanza | ¿Cómo marcos regulatorios inciden en decisiones de adopción? | MEDIUM |

Ver [POCKETS_DELIMITACION.md](POCKETS_DELIMITACION.md) para queries curadas, criterios de aceptación y papers de referencia.

---

## Fuentes de búsqueda (4 APIs libres)

| Fuente | Mejor para |
|--------|-----------|
| Semantic Scholar | CS e interdisciplinario |
| NBER | Economía: Autor, Acemoglu, Brynjolfsson |
| OpenAlex | Journals + conteos de citas |
| ArXiv | Preprints CS/AI muy recientes |

---

**Ver [AGENT.md](AGENT.md) para documentación completa.**