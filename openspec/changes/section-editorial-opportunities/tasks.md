## 1. Prerrequisitos de datos / engine

- [x] 1.1 Verificar (o completar en change/task previo) que `build_base_frame` consume `views_7d` real vía `load_real_views_targets` / `csv_urls` y que el train views corre end-to-end — ya implementado y verificado en `predict-views-impact` (r2_mean=0.490, ver ese change)
- [x] 1.2 Documentar en config el `target_kind` esperado (`views_7d` preferido) — `configs/editorial_opportunities.yaml` declara `target_kind: views_7d`
- [x] 1.3 Confirmar acceso a frame de notas con features actionable + target (nivel nota para receta) — `editorial_ops/data.py` construye este frame reusando `load_structured` + `load_real_views_targets` (agregado por nota) del engine

## 2. Clasificación actionable vs diagnostic

- [x] 2.1 Definir lista canónica `ACTIONABLE_FEATURES` / `DIAGNOSTIC_FEATURES` alineada al design — `src/shannon_model/impact_model/feature_kinds.py`
- [x] 2.2 Exponer helper consumible por la capa de receta — `feature_kind(feature_id)` + diccionarios importables
- [x] 2.3 Ajustar delta `views-impact-model` para inventario testeable — módulo standalone, importable/inspeccionable sin depender de correr el pipeline completo

## 3. Receta (paso 1)

- [x] 3.1 Crear paquete (ej. `src/shannon_model/editorial_ops/`) + config YAML
- [x] 3.2 Implementar filtro por scope (`categoria` | `all`) + `min_notes`
- [x] 3.3 Implementar `top_views_profile_v0`: cuantil alto → reglas (rangos/valores/bins) solo actionable
- [x] 3.4 Excluir autor/`source_*` de las reglas
- [x] 3.5 Serializar objeto `recipe` (reglas + labels + soporte)
- [x] 3.6 Mapear `lever_label` humanos (ej. `Hora pub.`)

## 4. Cumplimiento (paso 2)

- [x] 4.1 Evaluar cada nota actual del scope (ventana compliance configurada) contra la receta
- [x] 4.2 Aplicar `recipe_match_threshold` (default: cumplir todas las reglas)
- [x] 4.3 Emitir `notes_matching`, `notes_total`, `compliance_pct`
- [x] 4.4 Separar `compliance_pct` de `notas_analizadas_pct`

## 5. Mayor oportunidad + KPIs

- [x] 5.1 Por regla: medir compliance parcial + diferencial de views cumplen vs no
- [x] 5.2 Elegir tip primario por gap × impacto (`compliance_gap_v0`)
- [x] 5.3 Emitir `estimated_upside_views` + `method` + `target_kind`
- [x] 5.4 KPIs: `views_seccion`, `indice_shannon` provisional_recipe_compliance_v0 (o null)
- [x] 5.5 Caso `insufficient_data` sin inventar receta/upside

## 6. CLI y artefactos

- [x] 6.1 `configs/editorial_opportunities.yaml` (scopes, cuantiles, thresholds, periodo compliance, paths)
- [x] 6.2 `scripts/report_editorial_opportunities.py`
- [x] 6.3 Persistir JSON bajo `checkpoints/editorial_opportunities/` con `recipe` + compliance + KPIs por scope
- [x] 6.4 Confirmar path gitignored — confirmado, `checkpoints/*` ya cubre el subdirectorio nuevo

## 7. Verificación vs producto esperado

- [x] 7.1 Corrida scope `all`: artefacto tiene receta **antes**/junto a compliance (ambos presentes) — confirmado en `checkpoints/editorial_opportunities/report.json`
- [x] 7.2 Corrida por sección: `compliance_pct` coherente (0–100) y tip **sin** autor/source — confirmado, 7 scopes corridos, todos con `compliance_pct` en rango y `mayor_oportunidad` siempre una feature actionable (Hora de publicación / Longitud del título)
- [ ] 7.3 Validar con el equipo que el % de nav del dashboard se alimenta de `compliance_pct` (o documentar mapeo distinto) — **pendiente, requiere confirmación de producto/equipo, no verificable por código**
- [x] 7.4 Caso pocas notas → `insufficient_data` — confirmado con `min_notes` artificialmente alto (no inventa receta/upside)

**Hallazgo de la corrida real (con el default original `match_threshold=1.0`):** `compliance_pct` salía muy bajo (0.8%-6.15% según sección), porque la receta v0 generaba ~12 reglas y exigir todas simultáneas multiplica probabilidades bajas entre sí (ej. `hora_del_dia` compliance individual=14%, `num_palabras`=44%). Esto es exactamente el riesgo ya anticipado en design.md ("'Cumple todas las reglas' es más simple de explicar; relajar vía config si compliance queda siempre ~0%").

**Ajustes aplicados tras el hallazgo:**
1. Regla de título simplificada: `RECIPE_FEATURES` (nuevo, en `feature_kinds.py`) usa solo `largo_titulo` para título — `tiene_signo_pregunta`/`tiene_numero`/`tiene_mayusculas_excesivas` siguen siendo `actionable` (no diagnostic) pero ya no son reglas independientes de la receta. Reglas totales: 12 → 9.
2. `recipe_match_threshold` bajado de 1.0 a 0.7 en `configs/editorial_opportunities.yaml`.

Con ambos cambios, `compliance_pct` quedó en rango 35%-50% según sección — mucho más parecido al ejemplo del dashboard (71% Deportes) que el 0.8%-6.9% original. `hora_del_dia` sigue siendo la regla más restrictiva individualmente (14% compliance), pero con el umbral 0.7 ya no ahoga todo el resultado.

## 8. Fuera de alcance / follow-up

- [x] 8.1 NLP / UI / API fuera de este change — confirmado, no se tocó nada de eso
- [x] 8.2 Follow-up: fórmula canónica Índice Shannon; método contrafactual B; receta por canal si el producto lo pide — documentado como pendiente, no implementado en v0 (ya estaba en el design como fuera de alcance)
