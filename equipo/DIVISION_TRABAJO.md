# División del trabajo — Mini-Juztina (2 integrantes)

## Roles

| Rol | Responsable | Alcance |
|---|---|---|
| **A — Datos + RAG** | Alumno | Fuentes oficiales, limpieza, chunking, validación, embeddings, ChromaDB, retriever y pipeline RAG. |
| **B — LLM + App** | _(nombre)_ | Selección del LLM, guardrails, API FastAPI, historial, Streamlit, integración, despliegue y pruebas de UI. |

Completar nombres y disponibilidad horaria antes de empezar.

## Entregables oficiales

| Entregable | Artefactos | Responsable | Criterio de aceptación |
|---|---|---|---|
| **1. Repositorio de código fuente** | `src/`, `app/`, `tests/`, `prompts/`, `README.md`, `DECISIONS.md`, `docs/ARQUITECTURA.md` | Ambos (B lidera estructura) | Código limpio y documentado; sin secretos; reproducible; commits legibles. |
| **2. Manual de instalación y despliegue local** | `docs/MANUAL_INSTALACION.md`, `run.ps1` / `docker-compose.yml` | B (A revisa datos e índice) | Una persona externa replica el entorno desde cero y llega a la UI funcional. |
| **3. Demostración en vivo (offline)** | `docs/DEMO.md`, slides, `tests/report.md` | Ambos (A citas, B operación) | 3 casos correctos, citas verificadas, guardrails y panel visibles, sin red. |

Detalle, checklist y definición de terminado: `docs/ENTREGABLES.md`.

## Reparto por paso

| Fase | Paso | Tarea | A | B | Entregable |
|---|---|---|---|---|---|
| 0 | 1 | Confirmar equipo y roles | X | X | Tabla de roles + disponibilidad |
| 0 | 2 | Repo y estructura de carpetas | X | X | Este repo con `.gitignore` y README |
| 0 | 3 | Entorno local + Ollama | | **X** | `requirements.txt` + prueba offline |
| 0 | 4 | Definir stack en DECISIONS.md | X | **X** | `DECISIONS.md` actualizado |
| 1 | 5 | Descargar fuentes oficiales | **X** | | 2 PDFs en `data/raw/` con fecha |
| 1 | 6 | Limpiar y normalizar | **X** | | `data/clean/*.txt` |
| 1 | 7 | Chunking jerárquico por artículo | **X** | | `src/chunker.py` + `data/chunks/*.jsonl` |
| 1 | 8 | Validar dataset | **X** | | Reporte de validación |
| 2 | 9 | Generar embeddings | **X** | | `src/embedder.py` |
| 2 | 10 | Índice ChromaDB persistente | **X** | | `db/` con colección `legislacion_pe` |
| 2 | 11 | Retriever + 10 consultas de control | **X** | | `src/retriever.py` + resultados |
| 3 | 12 | Elegir LLM local (2–3 modelos) | | **X** | Tabla comparativa en `DECISIONS.md` |
| 3 | 13 | System prompt / guardrails | Revisa | **X** | `prompts/system_prompt.txt` |
| 3 | 14 | Pipeline RAG | **X** | Apoya | `src/rag_pipeline.py` |
| 3 | 15 | Pruebas de alucinaciones y límites | Apoya | **X** | `tests/test_guardrails.md` |
| 4 | 16 | API FastAPI (`POST /chat`, `GET /health`) | | **X** | `src/api.py` + Swagger |
| 4 | 17 | Historial de conversación (SQLite) | | **X** | Sesiones funcionales |
| 5 | 18 | Chat Streamlit | | **X** | `app/ui.py` en localhost:8501 |
| 5 | 19 | Panel de transparencia | Campos | **X** | Panel lateral con fuente y score |
| 5 | 20 | Estados y errores en la UI | | **X** | UI robusta |
| 6 | 21 | Integración end-to-end | X | **X** | Flujo UI ↔ API ↔ RAG ↔ DB |
| 6 | 22 | Batería de 20–30 consultas + offline | **X** | **X** | `tests/report.md` |
| 6 | 23 | Despliegue en un comando | | **X** | `run.ps1` o `docker-compose.yml` |
| 7 | 24 | Manual de instalación y despliegue local | Revisa | **X** | `docs/MANUAL_INSTALACION.md` |
| 7 | 24 | Documentación técnica y arquitectura | **X** | **X** | `docs/ARQUITECTURA.md` + informe final |
| 7 | 25 | Demo en vivo offline (3 casos) | **X** | **X** | `docs/DEMO.md` + slides + guion |

**Regla:** la columna marcada en negrita es la persona responsable; la otra revisa antes del hito.

## Contratos de integración (acordar antes de programar)

### 1. Chunk (salida de A, entrada de B)

```json
{
  "id": "CP-Art-121",
  "documento": "Código Penal",
  "titulo": "Título I",
  "capitulo": "Capítulo I",
  "articulo": "121",
  "texto": "...",
  "fuente": "SPIJ",
  "fecha": "2026-10-20"
}
```

### 2. Retriever (salida de A, la consume el pipeline)

```python
retrieve(query: str, k: int = 5) -> list[dict]
# [{"id": "CONST-Art-2", "texto": "...", "metadatos": {...},
#   "score": 0.88, "score_semantico": 0.86, "distancia": 0.28,
#   "match_id": "CONST-Art-2-s005"}, ...]
```

El retriever consulta los subchunks (`legislacion_pe_sub`), agrupa por
`parent_id` y devuelve el artículo completo. Si la colección de subchunks no
existe, usa `legislacion_pe` directamente.

### 3. API (contrato entre B y la UI)

`POST /chat`

```json
// request
{"mensaje": "¿Qué protege la libertad de expresión?", "sesion_id": "abc123"}

// response
{
  "respuesta": "...",
  "fuentes": [
    {
      "documento": "Constitución Política del Perú",
      "titulo": "Título I",
      "capitulo": "Capítulo I",
      "articulo": "2",
      "fragmento": "...",
      "score": 0.87
    }
  ],
  "en_alcance": true,
  "motivo": "en_alcance",
  "modo": "llm",
  "citas_invalidas": [],
  "requiere_revision": false,
  "latencia_s": 43.1
}
```

`GET /health` → `{"status": "ok", "ollama": true, "db": true}`

Valores acordados:

- `modo`: `llm`, `extractivo`, `sin_llm` o `guardrail`.
- `motivo`: `en_alcance`, `sin_sustento`, `fuera_de_alcance` o `sin_llm`.
- En `guardrail`, `fuentes` va vacío y no se ejecuta retrieval ni LLM.
- `advertencia` es opcional; si el LLM falla, el pipeline responde en modo
  `extractivo` y la UI debe mostrar la advertencia.

### 4. Reglas de citación

- `id` de chunk: `CONST-Art-<N>` para Constitución y `CP-Art-<N>` para Código Penal.
- El LLM cita `[S1]`, `[S2]`, `[S3]`; el pipeline los reemplaza por
  `(Documento, Artículo N)` y agrega la sección “Fuentes”.
- Nunca cortar un artículo entre dos chunks canónicos; los subchunks solo se
  usan para recuperar y siempre se devuelve el artículo padre.
- Toda respuesta debe poder rastrearse a un `id` existente en `data/chunks/`.

## Reglas de colaboración

- Ramas: `feat/datos-rag` (A) y `feat/app-llm` (B). `main` solo recibe merges revisados.
- Commits pequeños y en español: `feat(chunker): separar por artículo`.
- Sync de 15 minutos lunes, miércoles y viernes; registrar bloqueos en `equipo/`.
- Definition of Done: código corre local, entregable existe, otra persona lo pudo ejecutar siguiendo el manual y la demo funciona offline.
- No subir PDFs gigantes ni `db/` si el repo se vuelve pesado; acordar antes.
- Todo entregable debe estar enlazado desde `README.md` y registrado en `docs/ENTREGABLES.md`.

## Cronograma (4 semanas)

| Semana | Pasos | Hito |
|---|---|---|
| 1 | 1–8 | Datos limpios + chunks validados |
| 2 | 9–15 | Índice vectorial + RAG con guardrails |
| 3 | 16–20 | API + UI con panel de transparencia |
| 4 | 21–25 | Integración, pruebas offline, documentación y demo |

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| PDFs oficiales difíciles de parsear | Validar con 3 artículos conocidos; ajustar regex de títulos/capítulos. |
| El LLM inventa citas | Guardrail de "no sustento", temperature 0.2 y verificación contra `id` del chunk. |
| Equipo sin GPU lento | Usar `qwen2.5:3b`; limitar `num_ctx` y `k`. |
| Retraso en integración | Contratos de arriba congelados al final de la semana 2; usar datos mock si falta una parte. |
| Dependencia de internet | Descargar modelos y PDFs en semana 1; prueba offline real en semana 4. |
