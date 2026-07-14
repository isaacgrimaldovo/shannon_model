## Context

Producto esperado (lenguaje de negocio):

> Con base en las views de las notas, identificar patrones de cómo las características influyen en más/menos vistas.  
> **Primero** calcular la **receta**; **después** decir cuántas de las **notas actuales** cumplen esa receta.

El UI del dashboard encaja con ese loop:

```
Views + features ──▶ RECETA (patrones ganadores)
                           │
                           ▼
              Notas actuales del periodo/sección
                           │
                           ▼
              % cumplimiento ──▶ Mayor oportunidad (regla con más gap)
```

Los % por sección en la nav (ej. Deportes 71%) se interpretan en v0 como **compliance de la receta** de esa sección (u homólogo documentado). Índice Shannon / Mayor oportunidad se derivan de receta + gaps, no del top SHAP de autor/canal.

Insumos: `notes_structured.parquet`, `csv_urls` → `views_7d`, engine `impact_model/`.

## Goals / Non-Goals

**Goals:**
- Aprender una **receta** por scope (sección | `all`) sobre features accionables vs views.
- Medir **cumplimiento** de notas actuales vs esa receta.
- Derivar KPIs + Mayor oportunidad desde gaps de cumplimiento (no desde atribución).
- Persistencia auditable (`target_kind`, método de receta, reglas, compliance).

**Non-Goals:**
- UI dashboard.
- Receta basada en autor o canal de tráfico.
- NLP tono/polaridad en v0.
- Reemplazar `predict-views-impact` como engine.
- Serving online.
- Cableado `views_7d` en `build_base_frame` como deliverable único — es prerrequisito.

## Decisions

**1. Pipeline obligatorio: Receta → Compliance → Oportunidad.**
No se emite solo un tip SHAP suelto. El artefacto SIEMPRE incluye:
- `recipe`: lista de reglas/rangos sobre features actionable
- `compliance`: `notes_matching` / `notes_total` / `compliance_pct`
- `mayor_oportunidad`: regla con mayor potencial (gap × impacto)

**2. Cómo se calcula la receta (v0).**
Método `top_views_profile_v0` (auditable, sin NLP):
1. Dentro del scope, tomar el subconjunto de alto desempeño (default: top 25% por target de views a nivel nota; config `recipe_top_quantile`).
2. Sobre features **actionable**, estimar el perfil “ganador”:
   - numéricas continuas → rango intercuartil (o mediana ± banda) del top
   - binarias/flags → valor mayoritario del top (umbral de prevalencia, ej. ≥60%)
   - hora de publicación → bin/moda de hora (o ventana horaria) del top
3. Cada regla tiene: `feature_id`, `operator`/`range`, `lever_label`, `support` (cuántas notas top la respaldan).
4. Autor/canal **no** entran en la receta.

Método alternativo futuro `shap_driven_recipe_v1`: usar importancia SHAP actionable para priorizar *qué* reglas incluir, pero los umbrales siguen saliendo del perfil top-views (evita tips de attribution).

**3. Cumplimiento (compliance).**
Una nota **cumple la receta** en v0 si satisface **al menos `recipe_match_threshold`** de las reglas (default: todas = 1.0, o fracción configurable ej. 0.7).  
`compliance_pct = 100 * notes_matching / notes_in_scope_usable`.

**Actualización (post-implementación):** con `match_threshold=1.0` y ~12 reglas, la corrida real dio `compliance_pct` de 0.8%-6.15% — exigir todas las reglas simultáneas multiplica probabilidades bajas entre sí. Se ajustó el default a **0.7** en `configs/editorial_opportunities.yaml`, quedando en rango 35%-50%, más cercano al ejemplo del dashboard (71% Deportes). También se simplificó la regla de título a una sola (`largo_titulo`, ver decisión 2) en vez de 4, vía un nuevo `RECIPE_FEATURES` (subconjunto de `ACTIONABLE_FEATURES` que sí entra a la receta v0).

Esto alimenta:
- el % por sección del dashboard (interpretación v0)
- parte del Índice Shannon provisional

**4. Mayor oportunidad.**
Entre las reglas de la receta, elegir la de mayor score:

`score = (1 - rule_compliance_pct) * rule_impact`

donde `rule_impact` v0 = diferencia de views medias (o mediana) entre notas que cumplen vs no cumplen esa regla dentro del scope (mismo target).  
Emitir label humano + `estimated_upside_views` ≈ gap de notas que no cumplen × diferencial de views (método `compliance_gap_v0`). Documentar que no es A/B de producción.

**5. Features actionable / diagnostic.**
Igual que antes: temporales, forma título/cuerpo, imágenes reales, flags, subtítulos, video…  
Diagnostic (fuera de receta/tip): `autor_*`, `source_*`, ids.

**6. Scope.**
Receta **por sección** cuando el filtro UI es una categoría; receta **global** para `all`. v0 calcula receta directamente en el subset del scope (no exige modelo por sección aparte). Umbral `min_notes` aplica a notas usables del scope antes de emitir receta.

**7. KPIs.**
- `compliance_pct` / conteos: cumplimiento de receta (notas actuales del scope en la ventana configurada).
- `notas_analizadas_pct`: cobertura de datos (features+target) — distinto de compliance.
- `views_seccion`: suma de vistas del target documentado.
- `indice_shannon` provisional_v0: score derivado de compliance + calidad/soporte de la receta (ej. escalar compliance_pct y diferencial top vs resto); marcar `indice_shannon_definition: "provisional_recipe_compliance_v0"`. Sustituir cuando exista fórmula canónica del diccionario.

**8. Periodo dashboard.**
Default v0: la **receta** se aprende sobre la ventana histórica disponible (ej. 90 días / dataset train); el **cumplimiento** se mide sobre las notas del **periodo del reporte** (ej. 07–14 jul) si está configurado; si no hay periodo, compliance = sobre el mismo pool usable del scope.

**9. Artefactos + prerreq target.**
Salida `checkpoints/editorial_opportunities/`. Declarar `target_kind`. Preferir `views_7d`.

## Risks / Trade-offs

- [Riesgo] Receta por correlación top-views ≠ causalidad. **Mitigación**: lenguaje “patrón asociado”, upside no = promesa A/B.
- [Riesgo] Top 25% puede estar dominado por breaking/outliers. **Mitigación**: opcional excluir breaking cuando exista; trim de percentil extremo configurable.
- [Riesgo] Reglas en features estructurales débiles → receta pobre. **Mitigación**: reportar `recipe_strength` / soporte; NLP en v1.
- [Trade-off] “Cumple todas las reglas” vs “cumple K de N”: default estricto (1.0) es más simple de explicar; relajar vía config si compliance queda siempre ~0%.

## Open Questions

- ¿Los % de la nav del dashboard son exactamente `compliance_pct` de la receta? (v0 asume que sí.)
- ¿Fórmula canónica Índice Shannon vs `provisional_recipe_compliance_v0`?
- ¿Una nota debe cumplir **todas** las reglas o un umbral K/N?
- ¿Timezone / bins de hora para la regla `Hora pub.`?
- ¿Receta distinta por canal (`source`) alguna vez, o siempre features editoriales cross-canal (agregando views a nivel nota)?
- ¿Autor como control en un modelo auxiliar sí/no, sin entrar a la receta?
