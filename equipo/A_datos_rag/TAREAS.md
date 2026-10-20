# Rol A — Datos + RAG

**Responsable:** Alumno
**Objetivo:** entregar a B un corpus limpio, chunkificado, indexado y un `retrieve()` estable.

## Semana 1 — Datos

- [x] **Paso 5.** Descargar Constitución y Código Penal vigentes desde SPIJ / Congreso / TC.
  - Guardar en `data/raw/` con nombre claro y fecha de descarga.
  - Anotar URL y fecha en `data/raw/FUENTES.md`.
- [x] **Paso 6.** Convertir a texto con `pdfplumber` y limpiar encabezados, pies, numeración y tildes.
  - Entregar `data/clean/constitucion.txt` y `data/clean/codigo_penal.txt`.
- [x] **Paso 7.** Implementar `src/chunker.py`.
  - Regex para Título, Capítulo y Artículo.
  - Un chunk = un artículo completo, con el esquema JSON acordado.
  - Entregar `data/chunks/constitucion.jsonl` y `data/chunks/codigo_penal.jsonl`.
- [x] **Paso 8.** Validar: nº de artículos esperado, sin truncamientos, metadatos completos.
  - Entregar reporte corto en `tests/validacion_dataset.md`.

**Hito semana 1:** corpus validado y contratos de chunk congelados.

## Semana 2 — Índice y RAG

- [x] **Paso 9.** `src/embedder.py` con `intfloat/multilingual-e5-base`.
  - Prefijos `passage:` para documentos y `query:` para consultas.
- [x] **Paso 10.** Crear colección `legislacion_pe` en ChromaDB persistida en `db/`.
  - Verificar que sobrevive al reinicio.
- [x] **Paso 11.** `src/retriever.py` con `retrieve(query, k=5)`.
  - Probar 10 consultas de control y guardar resultados (`tests/retrieval_control.md`).
- [x] **Paso 14.** `src/rag_pipeline.py`: query → retrieve → prompt → Ollama → JSON.
  - Coordinar con B el formato exacto de `{respuesta, fuentes}`.

**Hito semana 2:** índice persistente + retriever + pipeline RAG funcionando con el LLM de B.

## Semana 3 — Apoyo a integración

- [ ] Definir con B los campos del panel de transparencia (documento, título, capítulo, artículo, fragmento, score).
- [x] Revisar que las citas de la API correspondan a chunks reales.
- [x] Ajustar chunking o recuperación si las pruebas de B muestran fallos de contexto.

## Semana 4 — Pruebas, entregables y demo

- [ ] **Paso 22.** Diseñar 20–30 consultas (dentro/fuera de alcance/ambiguas) y validar respuestas contra el texto legal real.
- [ ] **Paso 24 (informe).** Documentar en el informe: fuentes, limpieza, chunking, embeddings, métricas de recuperación y limitaciones.
- [x] **Paso 24 (manual).** Aportar y revisar en `docs/MANUAL_INSTALACION.md` las secciones de descarga de fuentes, ingesta, chunking, embeddings e inicialización de la base vectorial.
- [ ] **Entregable 1.** Revisar que `src/` esté limpio, documentado y sin rutas absolutas ni secretos.
- [ ] **Paso 25 (demo).** Preparar y verificar el caso con cita correcta y el caso "sin sustento"; contrastar ambos contra el PDF oficial.
- [ ] **Paso 25 (ensayo).** Ensayar la demo completa sin red y registrar latencias.

## Archivos que te pertenecen

```
data/raw/FUENTES.md
data/clean/*.txt
data/chunks/*.jsonl
src/ingest.py
src/chunker.py
src/build_subchunks.py
src/embedder.py
src/retriever.py
src/rag_pipeline.py
src/validate_dataset.py
src/evaluate_retrieval.py
tests/validacion_dataset.md
tests/retrieval_control.md
docs/MANUAL_INSTALACION.md  (secciones de datos e índice)
docs/DEMO.md                (casos 1 y 3)
docs/ARQUITECTURA.md        (capa de datos y recuperación)
```
