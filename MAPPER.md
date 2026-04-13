# MAPPER.md - Construcción de Grafo Temático y Detección de Gaps

## Objetivo
Construir un grafo de papers donde nodos = papers y edges = relaciones semánticas. Detectar clusters temáticos, hubs, y gaps explícitos en cobertura.

---

## Arquitectura del Grafo

### Nodos
- **Atributos**: id, título, autores, año, venue, score, pockets, keywords
- **Cardinality**: >20 nodos (meta DO)

### Edges
- **Tipo 1: Citación**: A cita B (dirigido, weight=1)
- **Tipo 2: Tema compartido**: A y B comparten ≥2 keywords (no dirigido, weight=similarity)
- **Tipo 3: Espacio + tiempo**: Papers del mismo región/período (no dirigido, weight=0.5)

---

## Algoritmos

### 1. **Detección de Clusters (Louvain)**
- Input: Grafo de papers
- Output: Clusters {cluster_id: [paper_ids]}
- Interpretación: Cluster ≥5 nodos = "research area"

### 2. **Degree Centrality**
- Top hubs (degree >5) = influential papers
- Flag para visualización

---

## Detección de Gaps

### Gap 1: Metodológico
- RCT vs Panel vs Observational distribution
- Flag: "RCT domina, poco panel/observacional en contexto LATAM"

### Gap 2: Geográfico
- Authors affiliations + samples distribution
- Flag: "EEUU/Europa dominan, LATAM underrepresented"

### Gap 3: Temporal
- Distribution por año
- Flag: "Recent papers (2025-2026) scant"

### Gap 4: Temático (Pockets)
- Papers por pocket distribution
- Flag: "Worker/task cubiertos, team sparse"

### Gap 5: Outcome Types
- Outcomes medidos distribution
- Flag: "Innovation outcomes rarely measured"

---

**Última actualización**: 2026-04-13  
**Status**: Listo para implementación
