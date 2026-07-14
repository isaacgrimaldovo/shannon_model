## ADDED Requirements

### Requirement: Inventario de features actionable vs diagnostic
El sistema SHALL exponer (en código, config o artefacto del engine) una clasificación de features del modelo de impacto en vistas como `actionable` (palanca editorial) o `diagnostic` (atribución/identidad), de forma que la capa de oportunidades editoriales pueda filtrar tips sin hardcode disperso e inconsistente.

#### Scenario: Lista consumible por el reporte editorial
- **WHEN** se solicita la clasificación de features del training frame activo
- **THEN** las features de autor derivadas y de canal `source_*` están marcadas `diagnostic`
- **AND** las features estructurales editables listadas en el design de `section-editorial-opportunities` están marcadas `actionable` cuando existen en el frame

#### Scenario: Compatibilidad con el ranking SHAP crudo
- **WHEN** se genera la tabla SHAP completa del engine
- **THEN** la tabla puede seguir incluyendo features diagnostic
- **AND** eso no viola este requirement (el filtrado de tips ocurre en la capa de oportunidades)
