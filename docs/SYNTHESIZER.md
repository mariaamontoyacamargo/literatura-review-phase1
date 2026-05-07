# SYNTHESIZER.md - Extracción de Insights y Metadatos

## Objetivo
Extraer información estructurada de papers aceptados para alimentar el Mapper con insights semánticos.

---

## JSON Schema Estándar

```json
{
  "id": "paper_id",
  "titulo": "string",
  "autores": ["string"],
  "año": "int",
  "venue": "string",
  "link": "string",
  "abstract": "string",
  "metodologia": {
    "tipo": "RCT|cuasi-experimental|panel|observacional|teórico",
    "descripcion": "string"
  },
  "outcomes_principales": [
    {
      "outcome": "string",
      "efecto_magnitud": "string",
      "significancia": "p-value",
      "heterogeidad": "string"
    }
  ],
  "pockets_cubiertos": ["task", "worker", "team", "firm"],
  "keywords": ["AI", "productivity", "adoption"],
  "limitaciones": ["string"],
  "relaciones_semanticas": {
    "cita_a": ["paper_id_1"],
    "es_citado_por": ["paper_id_2"]
  },
  "notas": "string"
}
```

---

**Última actualización**: 2026-04-13  
**Status**: Listo para implementación
