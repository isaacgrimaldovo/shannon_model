# Tasks: training-foundation-next

## 1. Acuerdo y datos

- [ ] 1.1 Acordar fuente del dataset real (Drive / URL / Kaggle / otra) y documentarla en design o README
- [ ] 1.2 Definir layout de `data/raw` y `data/processed` para el dataset real
- [ ] 1.3 Implementar loader real detras de config, con fallback a sinteticos
- [ ] 1.4 Verificar entrenamiento local con muestra real (smoke)

## 2. Arquitectura

- [ ] 2.1 Especificar arquitectura final (capas, I/O, metricas) en design o delta spec
- [ ] 2.2 Implementar modelo y seleccion por `model.name` en config
- [ ] 2.3 Mantener `ShannonBaseline` usable via config hasta deprecacion explicita
- [ ] 2.4 Smoke test local + comparacion metricas vs baseline si aplica

## 3. Experiment tracking

- [ ] 3.1 Definir backend (W&B u otro) y variables en `.env.example`
- [ ] 3.2 Integrar logging opcional (off por defecto)
- [ ] 3.3 Documentar como activar tracking en local y Colab

## 4. Colab y cierre SDD

- [ ] 4.1 Actualizar `notebooks/colab_train.ipynb` solo si hace falta para datos/Drive
- [ ] 4.2 Actualizar `docs/COLABORACION.md` / README con el flujo nuevo
- [ ] 4.3 Validar specs (`openspec validate training-foundation-next`) y archivar change
