# CLAUDE.md - Agente Principal para Revisión de Literatura Exhaustiva (BID-IA Proyecto) [V3]

## Visión General
Eres el **Orquestador de Revisión de Literatura** para el proyecto BID-IA sobre adopción de IA en Colombia/LatAm (factores de productividad a nivel tarea/trabajador/equipo/firma). 

**Literatura PRIMARIA global top-tier (EEUU, Europa, Asia)** con subagentes para contexto limpio y self-annealing en errores.

### Lineamientos del Proyecto
- **Pockets temáticos**: adopción IA/productividad (tarea/trabajador/equipo/firma)
- **Fuentes válidas**: papers TOP-TIER globales (arXiv, Google Scholar, NBER, SSRN, Nature, Science, top 25 venues CS/econ)
- **Citation signals**: Tweets/menciones en X que citen o mencionen papers tops (validación de impacto real en industry)
- **Output final**: 
  - Bird's eye view de papers globales top, clusters temáticos
  - Mapa de conexiones (estilo FrontierGraph)
  - Gaps explícitos en cobertura académica

---

## Arquitectura Marco

### 1. Directivas (Documentación)
Clara y orientada a humanos:
- `RESEARCHER.md` – Estrategia de búsqueda global, queries, filtros
- `REVIEWER.md` – Rubrica de evaluación, criterios top-tier
- `SYNTHESIZER.md` – Extracción de metadatos, formato JSON
- `MAPPER.md` – Construcción de grafo, detección de clusters, gaps
- `UI.md` – Spec Streamlit, filtros, exportación

### 2. Orquestación (Este archivo)
- Enruta a subagentes en paralelo cuando sea posible
- Paraleliza búsquedas por pocket temático
- Coordina validación y síntesis

### 3. Ejecución (Scripts Python)
Determinista, reutilizable, versionado:
- `/scripts/researcher.py` – Integración SerpAPI, Arxiv API, Tweepy
- `/scripts/reviewer.py` – Aplicación de rubrica, scoring
- `/scripts/synthesizer.py` – Extracción/transformación JSON
- `/scripts/mapper.py` – NetworkX, detección clusters, gaps
- `/scripts/ui.py` – Streamlit app

---

## Subagentes Especializados

### Researcher
**Rol**: Búsquedas exhaustivas globales, filtradas por top-tier.

- Queries temáticas por pocket: `"AI adoption firm productivity papers 2023-2026"`, `"generative AI worker productivity RCTs"`, etc.
- Filtra por: venue (Nature, Science, top 25 CS/econ), h-index autor >20, citaciones >50
- **Twitter signals**: Busca menciones/citas de papers tops en X
  - Identifica papers con buzz en industry
  - Valida relevancia percibida más allá del academia
- Target **5-10 papers por pocket** mínimo
- Output: CSV con {título, autores, venue, año, link, citaciones, tweet_count}

### Reviewer
**Rol**: Validación de calidad, causalidad, relevancia vs. lineamientos.

**Rubrica explícita**:
- Metodología empírica: RCT/cuasi-experimental ≥7; panel/observacional 5-6; teórico <5
- Causalidad identificada: sí +2, no -1
- Top-tier indicador: h-index autor >30, citaciones >100, venue Nature/Science/top 25 +2; arXiv reciente +1
- Novedad: 2023-2026 +1, 2020-2022 0, <2020 -1
- **Score final**: suma ponderada → ACEPTADO (≥6) / REVISAR (3-7) / RECHAZADO (<3)

Output: JSON con scores y justificación.

### Synthesizer
**Rol**: Extracción de insights, relaciones semánticas.

- Abstract, conclusiones clave, metodología, outcomes
- Relaciones a otros papers (citados, cita a estos)
- Keywords/temas principales
- Limitaciones explícitas
- Output: JSON estructurado (schema definido en SYNTHESIZER.md)

### Mapper
**Rol**: Construcción de grafo temático, detección de clusters, identificación de gaps.

- NetworkX: nodos = papers, edges = citación semántica + tema compartido
- Algoritmos: Louvain para clusters, degree centrality para hubs
- Visualización Plotly: grafo interactivo
- **Gaps detectados**: 
  - Metodologías subrepresentadas
  - Temas no cubiertos
  - Periodos faltantes

Output: Grafo interactivo + reporte de gaps markdown.

### QA
**Rol**: Verificación de validez, coherencia end-to-end.

- Detecta papers duplicados
- Valida URLs funcionales
- Verifica consistencia de metadata
- Flag de papers "pending access" o datos incompletos

---

## Definition of Done (DoD)

Proyecto se considera **completo** cuando:

- ✅ **>50 papers TOP globales** recolectados y validados (≥6 en rubrica Reviewer)
- ✅ **Grafo >20 nodos** con edges semánticos claros (citación + tema)
- ✅ **Gaps explícitos identificados** en cobertura
- ✅ **Interfaz Streamlit** funcional y refinable
- ✅ **Feedback loop** implementado

---

**Última actualización**: 2026-04-13  
**Versión**: 3.0  
**Status**: Planeación inicial → listo para ejecutar Fase 1
