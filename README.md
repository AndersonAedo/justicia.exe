# Mini-Juztina

Asistente legal 100% local especializado en la **Constitución Política del Perú** y el **Código Penal peruano**. Usa RAG (recuperación + generación) con Ollama, ChromaDB y embeddings multilingües; no envía datos a servicios en la nube.

## Estado

Rol A (datos + RAG) implementado y validado: corpus, chunks, subchunks, índice
ChromaDB, retriever híbrido y pipeline RAG. Rol B (API, guardrails, UI) en
integración. Ver `equipo/DIVISION_TRABAJO.md` y `equipo/Alumno/ESTADO.md`.

## Entregables

| Entregable | Artefacto |
|---|---|
| **Repositorio de código fuente** | `src/`, `app/`, `tests/`, `prompts/`, `README.md`, `DECISIONS.md` y `docs/ARQUITECTURA.md` |
| **Manual de instalación y despliegue local** | [`docs/MANUAL_INSTALACION.md`](docs/MANUAL_INSTALACION.md) |
| **Demostración en vivo (offline)** | [`docs/DEMO.md`](docs/DEMO.md) + slides |
| **Control de entregables y criterios de aceptación** | [`docs/ENTREGABLES.md`](docs/ENTREGABLES.md) |

## Estructura

```
mini-juztina/
├── data/raw/        # PDFs oficiales (SPIJ, Congreso, TC)
├── data/clean/      # texto limpio
├── data/chunks/     # JSONL con metadatos (un artículo por chunk)
├── data/subchunks/  # fragmentos por inciso para recuperación
├── db/              # índice vectorial persistente (ChromaDB)
├── src/             # ingesta, chunking, embeddings, retriever, RAG, API
├── app/             # frontend Streamlit
├── prompts/         # system prompt y plantillas
├── tests/           # pruebas y reportes
├── docs/            # manual, arquitectura, demo y entregables
├── equipo/          # reparto de trabajo y checklists
├── requirements.txt
├── DECISIONS.md
└── README.md
```

## Requisitos

- Python 3.10+
- [Ollama](https://ollama.com/) instalado y funcionando offline
- 16 GB de RAM recomendados, 20 GB de disco libre
- GPU opcional

## Instalación rápida (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Modelo local (ver DECISIONS.md)
ollama pull qwen2.5:3b
ollama serve
```

> Guía completa desde cero (Ollama, fuentes, índice, offline y solución de problemas): [`docs/MANUAL_INSTALACION.md`](docs/MANUAL_INSTALACION.md).

## Ejecución del pipeline (rol A)

```powershell
python -m src.ingest --input data/raw --output data/clean
python -m src.chunker --input data/clean --output data/chunks
python -m src.build_subchunks
python -m src.embedder --chunks data/chunks --persist db --collection legislacion_pe
python -m src.embedder --chunks data/subchunks --persist db --collection legislacion_pe_sub
python -m src.validate_dataset
python -m src.evaluate_retrieval --k 5
python -m src.rag_pipeline "¿Qué protege la libertad de expresión?" --k 5 --json
```

La API y la UI las implementa el rol B sobre el contrato de
`equipo/DIVISION_TRABAJO.md`.

## Demo

El guion de la demostración en vivo (3 casos, prueba offline y rúbrica) está en [`docs/DEMO.md`](docs/DEMO.md).

## Equipo

- **A — Datos + RAG (Alumno):** `equipo/Alumno/ESTADO.md` · `equipo/A_datos_rag/TAREAS.md`
- **B — LLM + Backend/Frontend:** `equipo/B_llm_backend_frontend/TAREAS.md`
- **Reparto completo y contratos de integración:** `equipo/DIVISION_TRABAJO.md`

## Principios del proyecto

1. Todo corre localmente (LLM, embeddings y base vectorial).
2. Toda respuesta cita documento, artículo y fragmento textual.
3. Si no hay sustento en las fuentes, el asistente lo dice explícitamente.
4. Las consultas laborales, civiles o tributarias evidentes se declinan sin
   inventar una respuesta.
5. Nada de asesoría legal personalizada: es una herramienta informativa.
