# Alumno — Rol A: Datos + RAG

Carpeta de identificación y seguimiento del integrante **Alumno**, responsable
del corpus legal, la indexación y la recuperación para Mini-Juztina.

## Alcance

- Pasos 5–11 y 14: fuentes, limpieza, chunking, embeddings, ChromaDB,
  recuperación híbrida y pipeline RAG.
- Entrega a B: `retrieve(query, k=5)` estable y contrato JSON de fuentes.
- Apoyo en pruebas de aceptación, manual de instalación y demo.

## Contenido

- `ESTADO.md`: avance, evidencias, métricas y pendientes.
- `../../equipo/A_datos_rag/TAREAS.md`: checklist original del rol A.
- `../../data/raw/FUENTES.md`: URLs, fechas y hashes de los PDF.
- `../../tests/validacion_dataset.md`: control de calidad de los chunks.
- `../../tests/retrieval_control.md`: 10 consultas de control y métricas.

## Comandos rápidos

```powershell
# Activar entorno
.\.venv\Scripts\Activate.ps1

# Pipeline completo de datos
python -m src.ingest --input data/raw --output data/clean
python -m src.chunker --input data/clean --output data/chunks
python -m src.build_subchunks
python -m src.embedder
python -m src.embedder --chunks data/subchunks --collection legislacion_pe_sub

# Controles
python -m src.validate_dataset
python -m src.evaluate_retrieval --k 5

# Prueba RAG
python -m src.rag_pipeline "¿Qué protege la libertad de expresión?" --k 5 --modelo qwen2.5:3b --json
```

## Contacto / coordinación

- Rol B consume `src.retriever.retrieve()` y el JSON de
  `src.rag_pipeline.responder()`.
- Cualquier cambio de esquema de metadatos debe reflejarse en
  `docs/ARQUITECTURA.md` y en el panel de transparencia de B.
