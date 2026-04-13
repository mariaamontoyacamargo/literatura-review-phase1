# UI.md - Especificación Streamlit Dashboard

## Objetivo
Interfaz web interactiva, filtrable, explorable, que permita visualizar papers, grafo de conexiones, gaps, y exportar resultados.

---

## Tabs

### Tab 1: Papers (Tabla + Detalles)
- Tabla interactiva: Título, Autores, Año, Venue, Score, Citas
- Filtros: pocket, año, venue
- Click en paper → Modal con abstract, metodología, outcomes, keywords

### Tab 2: Graph (NetworkX Visualización Interactiva)
- Plotly: Nodos = papers (size = degree centrality)
- Edges = citación (rojo) + tema (azul)
- Color = pocket temático
- Click en nodo → Paper details

### Tab 3: Gaps (Reporte Interactivo)
- Metodológico: RCT % | Panel % | Observational %
- Geográfico: USA/EU % | LATAM %
- Temporal: distribution por año
- Temático: papers por pocket
- Outcomes: distribution de outcomes medidos

### Tab 4: About
- Project overview
- Data info
- Download options: CSV, JSON, BibTeX

---

## Sidebar Filtros
- Checkboxes: Pocket (multi-select)
- Slider: Año (range)
- Multi-select dropdown: Venue
- Search bar: free-text

---

**Última actualización**: 2026-04-13  
**Status**: Spec completo
