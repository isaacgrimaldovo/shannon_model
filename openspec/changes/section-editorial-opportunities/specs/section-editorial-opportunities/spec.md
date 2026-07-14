## ADDED Requirements

### Requirement: Pipeline receta luego cumplimiento
El sistema SHALL, para cada scope solicitado (categoría editorial o `all`), primero calcular una **receta** de características accionables asociada a mayor volumen de vistas, y después medir cuántas de las **notas actuales** del scope cumplen esa receta. El artefacto de salida SHALL incluir ambos resultados de forma explícita.

#### Scenario: Orden receta → compliance
- **WHEN** se genera el reporte editorial para un scope con suficientes notas
- **THEN** el artefacto contiene un objeto `recipe` con las reglas aprendidas
- **AND** contiene métricas de cumplimiento (`notes_matching`, `notes_total`, `compliance_pct`) calculadas contra esa misma receta
- **AND** no emite cumplimiento sin haber materializado la receta del scope

#### Scenario: Scope por sección
- **WHEN** el scope es una categoría (ej. deportes)
- **THEN** la receta y el cumplimiento se calculan solo con notas de esa categoría
- **AND** la categoría misma no es una regla de la receta

#### Scenario: Datos insuficientes
- **WHEN** las notas usables del scope son menores que `min_notes`
- **THEN** el sistema no inventa una receta con upside
- **AND** reporta `status: insufficient_data`

### Requirement: Receta basada en patrones views × características accionables
El sistema SHALL construir la receta identificando patrones de features **accionables** asociados a notas de mayor views dentro del scope, y SHALL NOT incluir en la receta features de autor ni de canal de tráfico.

#### Scenario: Perfil a partir de notas de alto desempeño
- **WHEN** se calcula la receta con el método v0 documentado
- **THEN** las reglas se derivan del perfil de features accionables del subconjunto de alto desempeño por views (cuantil configurable)
- **AND** cada regla incluye al menos `feature_id`, criterio (rango/valor/bin), `lever_label` y soporte

#### Scenario: Exclusión de attribution de la receta
- **WHEN** se generan las reglas de la receta
- **THEN** no aparecen `autor_avg_views`, `autor_num_notas`, ni features `source_*` (ni identity de autor/url) como reglas de la receta

#### Scenario: Pool actionable v0
- **WHEN** se eligen candidatas a reglas en v0
- **THEN** solo se usan features estructurales editables (temporales de publicación, forma de título/cuerpo, imágenes reales, flags de título, subtítulos, video embed, y análogas del design)
- **AND** no se requieren features NLP de tono/polaridad para completar v0

### Requirement: Cumplimiento de la receta sobre notas actuales
El sistema SHALL reportar qué proporción de las notas actuales del scope (ventana de compliance configurada) cumplen la receta según el umbral de match documentado.

#### Scenario: Porcentaje y conteos de cumplimiento
- **WHEN** la receta del scope está disponible
- **THEN** el sistema calcula `notes_matching`, `notes_total` y `compliance_pct`
- **AND** una nota cuenta como matching solo si satisface el criterio de match de la receta (`recipe_match_threshold`)

#### Scenario: Compliance distinto de cobertura de datos
- **WHEN** se emiten KPIs del scope
- **THEN** `compliance_pct` (notas que siguen la receta) se reporta por separado de `notas_analizadas_pct` (notas con features+target usables / elegibles)

### Requirement: Mayor oportunidad desde gaps de cumplimiento
El sistema SHALL derivar la Mayor oportunidad a partir de las reglas de la receta con mayor gap de cumplimiento ponderado por impacto en views, no a partir del top SHAP crudo de features diagnostic.

#### Scenario: Tip primario desde regla de receta
- **WHEN** existe al menos una regla actionable con notas que no cumplen
- **THEN** se emite una Mayor oportunidad primaria con `lever_label`, `feature_id` (regla), `estimated_upside_views`, `method`, `scope` y `n_notes`

#### Scenario: Tip no copia attribution SHAP
- **WHEN** la feature global con mayor |SHAP| es autor o `source_*`
- **THEN** esa feature no se elige como Mayor oportunidad
- **AND** el tip permanece dentro de las reglas de la receta actionable

#### Scenario: Upside auditable
- **WHEN** se informa `estimated_upside_views`
- **THEN** el artefacto declara `method` (ej. `compliance_gap_v0`) y `target_kind`
- **AND** el valor no se presenta como resultado de un A/B de producción

### Requirement: KPIs alineados al dashboard Shannon
El sistema SHALL emitir, por scope, el paquete necesario para el dashboard: cumplimiento de receta, cobertura de análisis, views de sección, Índice Shannon (provisional o canónico), y Mayor oportunidad.

#### Scenario: Views y cobertura
- **WHEN** se genera el reporte
- **THEN** incluye `views_seccion` (suma del target documentado) y `notas_analizadas_pct`

#### Scenario: Índice Shannon ligado a receta/compliance
- **WHEN** no hay fórmula canónica adoptada del diccionario
- **THEN** el sistema emite `indice_shannon` según definición provisional basada en receta/cumplimiento (`provisional_recipe_compliance_v0`) o `null` con razón si se configura omitir
- **AND** declara `indice_shannon_definition` en el artefacto

#### Scenario: Artefacto persistido
- **WHEN** el reporte termina sin error
- **THEN** se persiste un artefacto estructurado (JSON o tabular) fuera de control de versiones con `recipe`, compliance y KPIs por scope generado

### Requirement: Separación engine de predicción vs capa de receta
El sistema SHALL reutilizar el dataset/modelo de `views-impact-model` como soporte cuando convenga, pero la salida de producto de este capability es la receta + compliance + tip, no el ranking SHAP crudo.

#### Scenario: Consumo del inventario actionable
- **WHEN** se arma la receta
- **THEN** el sistema usa la clasificación actionable vs diagnostic expuesta por el engine (o lista canónica equivalente)
- **AND** ignora diagnostic al formular reglas y tips
