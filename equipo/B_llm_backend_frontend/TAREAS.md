# Rol B — LLM + Backend/Frontend

**Responsable:** _(nombre)_
**Objetivo:** elegir el LLM, definir guardrails, exponer la API y construir la UI con panel de transparencia.

## Semana 1 — Entorno y LLM

- [ ] **Paso 3.** Crear venv, instalar `requirements.txt`, verificar Ollama offline con un modelo pequeño.
- [ ] **Paso 12 (inicio).** Probar 2–3 modelos en español (`llama3.1:8b`, `qwen2.5:7b`, opcional 3B) con 5 prompts legales.
  - Medir precisión, citas correctas y latencia; registrar en `DECISIONS.md`.
- [ ] **Paso 13 (borrador).** Redactar `prompts/system_prompt.txt` con rol, límites, citas y formato fijo.

**Hito semana 1:** entorno reproducible + decisión preliminar de LLM + prompt borrador.

## Semana 2 — Guardrails

- [ ] **Paso 12 (cierre).** Confirmar modelo y configuración `temperature=0.2`, `num_ctx>=4096`.
- [ ] **Paso 15.** Probar alucinaciones y límites:
  - dentro de alcance con cita,
  - fuera de alcance (declina),
  - sin sustento (no inventa).
  - Guardar `tests/test_guardrails.md` y ajustar el prompt.
- [ ] Revisar con A el contrato `{respuesta, fuentes}` del pipeline.

**Hito semana 2:** guardrails validados con ejemplos documentados.

## Semana 3 — API y UI

- [ ] **Paso 16.** `src/api.py` con FastAPI: `POST /chat`, `GET /health`, Swagger en localhost:8000.
- [ ] **Paso 17.** Historial por sesión en SQLite, limitado a los últimos N turnos.
- [ ] **Paso 18.** `app/ui.py` en Streamlit: historial, input, botón limpiar.
- [ ] **Paso 19.** Panel lateral de transparencia: documento, título, capítulo, artículo, fragmento y score.
- [ ] **Paso 20.** Estados: "pensando…", Ollama caído, consulta fuera de alcance.

**Hito semana 3:** API + UI funcionando con datos reales de A.

## Semana 4 — Integración, entregables y demo

- [ ] **Paso 21.** Integración end-to-end UI ↔ API ↔ RAG ↔ DB.
- [ ] **Paso 22.** Ejecutar la batería de pruebas de A desde la UI y medir latencia; prueba offline real.
- [ ] **Paso 23.** `run.ps1` o `docker-compose.yml` que levante Ollama + API + UI; actualizar README.
- [ ] **Entregable 1.** Revisar arquitectura, estructura del repo, manejo de errores y ausencia de secretos; mantener `docs/ARQUITECTURA.md` y `DECISIONS.md`.
- [ ] **Paso 24 (manual).** Liderar `docs/MANUAL_INSTALACION.md`: requisitos, venv, dependencias, Ollama, API, UI, comando único, offline y solución de problemas.
- [ ] **Paso 24 (informe).** Documentar API, prompt, guardrails, limitaciones y trabajo futuro.
- [ ] **Paso 25 (demo).** Preparar el caso "fuera de alcance", la demostración offline y el panel de transparencia.
- [ ] **Paso 25 (ensayo).** Ensayar la demo completa con A y cronometrar ≤ 12 minutos.

## Archivos que te pertenecen

```
src/api.py
src/rag_pipeline.py  (integración con Ollama; coordinar con A)
app/ui.py
prompts/system_prompt.txt
tests/test_guardrails.md
tests/report.md
run.ps1 / docker-compose.yml
docs/MANUAL_INSTALACION.md
docs/DEMO.md
docs/ARQUITECTURA.md
docs/ENTREGABLES.md
DECISIONS.md (sección LLM)
```
