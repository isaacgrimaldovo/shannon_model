## 1. Celda de poll loop en el notebook

- [x] 1.1 Agregar celda markdown explicando el flujo: local commit+push -> Colab detecta -> corre `scripts/train.py` -> resultados en `checkpoints/` (o Drive si montado)
- [x] 1.2 Agregar celda de codigo con la funcion de poll loop: `git pull`, comparar SHA de HEAD contra ultimo SHA corrido, variable `poll_interval` configurable (default 20s)
- [x] 1.3 Implementar filtro de paths: `git diff --name-only <sha_anterior> <sha_nuevo>` y disparar solo si el diff toca `src/`, `scripts/` o `configs/`
- [x] 1.4 Invocar `scripts/train.py --config configs/default.yaml` (mismo entrypoint ya usado en el notebook) cuando el filtro de paths aprueba el cambio
- [x] 1.5 Loguear cada iteracion del loop: SHA detectado, si disparo run o no, y motivo (path filtrado / sin cambios / run ejecutado)
- [x] 1.6 Envolver el loop en `try/except KeyboardInterrupt` para terminar limpio ante "Interrupt execution" de Colab, sin dejar el `subprocess` colgado

## 2. Verificacion manual

- [ ] 2.1 Correr el notebook en Colab, hacer un push local que toque `configs/` y confirmar que el loop dispara el training dentro del intervalo de poll
- [ ] 2.2 Hacer un push local que solo toque `README.md` y confirmar que el loop NO dispara un nuevo training
- [ ] 2.3 Interrumpir el loop manualmente desde Colab y confirmar que corta sin dejar proceso colgado ni traceback confuso
