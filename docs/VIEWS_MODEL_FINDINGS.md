# Modelo de impacto en vistas — qué aprendimos

Bitácora de hallazgos del trabajo en `predict-views-impact` / `scrape-news-content`. Complementa `docs/FEATURES_BACKLOG.md` (qué features probar después) con el *por qué* de las decisiones ya tomadas.

## Línea de tiempo de resultados

| Momento | R² (CV) | Qué cambió |
|---|---|---|
| Baseline inicial (split 80/20 único, dataset completo) | 0.533 | — |
| CV fold-safe (5-fold, autor recalculado por fold) | **0.031** | Destapó fuga de datos de autor |
| + Tier 1 (título/cuerpo: signos, mayúsculas, párrafos, video) | 0.031 | Sin cambio — features agotadas |
| + granularidad url×source + GroupKFold | **0.098** | Fix real: dejar de mezclar canales |

El salto de 0.533 a 0.031 no es que el modelo haya empeorado — es que el primer número era falso (fuga). El salto de 0.031 a 0.098 sí es una mejora real.

## 1. Bugs de extracción (antes de cualquier modelado)

- **Encoding roto**: el sitio sirve UTF-8 pero no lo declara en `Content-Type`, `requests` caía a ISO-8859-1 por default → tildes/ñ corruptas (`Matías` → `MatÃ­as`). Fix: forzar `response.encoding = "utf-8"`.
- **`num_imagenes`/`tiene_img_principal` constantes**: el array `image` del JSON-LD siempre trae 3 variantes de resolución de la misma imagen hero, no el conteo real de imágenes del cuerpo. Sin varianza → sin señal, aunque el dato "existía". Fix: `num_imagenes_real` contando `<img>` reales dentro de `div.texto-noticia`.

Lección: un campo puede estar "extraído correctamente" según su fuente y aun así ser inútil para el modelo si esa fuente no mide lo que el nombre de la columna promete.

## 2. Fuga de datos de autor (el hallazgo más importante)

`autor_avg_views` (leave-one-out) se calculaba sobre el dataset COMPLETO, no por fold de entrenamiento. Con un solo split 80/20 esto no se notaba. Al correr 5-fold CV recalculando esa estadística fold-safe (`fit_author_stats` solo con datos de train de cada fold), el R² se desplomó de 0.533 a 0.031.

Con 3,406 notas y 128 autores (top 10 = 55% del dataset, 65 autores con 1 sola nota), el modelo de "0.533" no aprendía señal editorial — memorizaba qué autor prolífico escribió cada nota.

**Regla general que queda de esto**: cualquier feature derivada del target (target encoding, medias históricas, etc.) necesita recalcularse por fold en la validación cruzada. Un solo split no alcanza para detectar este tipo de fuga si el dataset es chico — recién se hizo evidente con el dataset completo.

## 3. Features baratas de contenido no alcanzan (Tier 1)

Se agregaron 9 features de parsing simple sin NLP: `num_letras`, `largo_titulo`, `num_imagenes_real`, `tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `num_parrafos`, `tiene_subtitulos`, `tiene_video_embed`. R² fold-safe: **sin cambio** (0.031 → 0.031). Las 9 quedaron al fondo de la tabla de impacto SHAP.

Correlación lineal cruda confirmó por qué: `num_palabras` ≈ 0.002, `num_etiquetas`/`num_imagenes_real`/`largo_titulo` ≈ 0.08-0.09 (débiles). La familia completa de señales "de forma" (cuánto mide el título, cuántas imágenes, etc.) está agotada para este target.

## 4. El problema real: mezclar canales de tráfico cancela señal

El target usado (`pageViewsTotal` sumado) mezcla 4 fuentes de tráfico muy distintas: Facebook, Google (orgánico), Google Discover (feed algorítmico), dark social (compartido directo/mensajería). Separar el target por canal y recalcular correlaciones mostró patrones **opuestos**:

| Feature | Mezclado | Google Discover | Facebook | Dark Social |
|---|---|---|---|---|
| `largo_titulo` | 0.094 | **0.196** | 0.022 | **-0.065** |
| `num_palabras` | -0.009 | -0.023 | **0.082** | 0.077 |

Título largo ayuda en Discover (feed algorítmico, vive de headline) y perjudica en dark social (compartido humano). Sumar todo promedia una señal positiva con una negativa → el modelo ve ruido donde hay dos fenómenos reales y contradictorios.

**Fix**: pasar de "una fila por nota" a "una fila por combinación nota×source", con `source` como feature one-hot. Esto exigió un ajuste adicional al CV: `GroupKFold` agrupando por `url`, porque ahora la misma nota aparece hasta 4 veces (una por canal) — sin esto, una nota podría tener su fila "Facebook" en train y su fila "Google" en validación en el mismo fold, repitiendo el mismo tipo de fuga que ya se había corregido para autor, pero a nivel nota.

Resultado: R² 0.031 → **0.098** (~3x), con desvío estándar más chico (0.024 → 0.015 — resultado más estable, no solo un fold con suerte). `source` aparece 2do-5to en la tabla de impacto, casi tan fuerte como autor.

## 5. Lo que NO explicaba el problema (verificado y descartado)

Antes de llegar al hallazgo de arriba, se probaron y descartaron otras hipótesis:

- **Outliers extremos**: el top 1% de notas (34 de 3,406) concentra 24% de las vistas totales. Se probó excluirlas — la correlación de las features NO cambió. No es el problema.
- **Antigüedad de la nota**: correlación entre días desde publicación y vistas es débil (-0.08). No hay un sesgo fuerte de "las notas viejas acumulan más vistas por estar más tiempo circulando".

Documentar los descartes importa tanto como los hallazgos — evita retestear las mismas hipótesis más adelante.

## 6. Dataset nuevo encontrado, todavía no usado

`data/raw/csv_urls/` (29 archivos CSV, ~1.6GB) trae granularidad **diaria** por URL sobre una ventana fija de 90 días, con 53,220 URLs únicas (vs 3,408 del dataset actual) en 9 categorías (3 nuevas: deportes, tecnologia, edicion-impresa). Esto permite calcular `views_7d` **real** (7 días exactos desde publicación, no un proxy agregado) para ~14,200 notas — de las cuales 2,825 ya están scrapeadas (target real gratis, sin scrapear nada nuevo). Las 11,375 restantes requieren scraping (~4.7 horas al ritmo actual).

Todavía no se incorporó al modelo — queda como la mejora más grande pendiente, junto con NLP (`tono`/`polaridad`, la feature que el diccionario de datos marca como más fuerte, requiere dependencia nueva).

## Estado actual

- R² fold-safe: **0.098 ± 0.015** (granularidad url×source, sin fuga de autor ni de nota).
- Top features: `autor_avg_views`, `source` (4 canales), `autor_num_notas` — el "quién" y "por dónde circuló" pesan más que el "cómo está escrita" la nota, con las features actuales.
- Siguiente palanca más prometedora: `views_7d` real (dataset nuevo) o NLP — ver `docs/FEATURES_BACKLOG.md`.
