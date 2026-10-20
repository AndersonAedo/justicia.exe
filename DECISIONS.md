# Registro de decisiones — Mini-Juztina

Formato por decisión: fecha, decisión, contexto, alternativas, justificación local y consecuencias.

---

## 2026-10-20 — Stack inicial

| Componente | Elección | Alternativas | Motivo (local / offline) |
|---|---|---|---|
| Backend | FastAPI | Flask, Django | Async, validación con Pydantic, Swagger automático; sin servicios externos. |
| Frontend | Streamlit | React, Gradio | Chat y panel lateral rápidos de implementar; corre local. |
| Vector DB | ChromaDB | FAISS, Qdrant | Persistencia simple en `db/`, metadatos y filtros; embebida, sin servidor. |
| Embeddings | intfloat/multilingual-e5-base | bge-m3, MiniLM | Buen rendimiento en español; se ejecuta local con sentence-transformers. |
| LLM | Ollama (`qwen2.5:3b` por defecto; 7b/8b opcionales) | llama.cpp, LM Studio | API local sencilla; modelos descargados una vez y uso 100% offline. |
| Historial | SQLite | JSON en disco, Postgres | Archivo local, sin servidor, suficiente para sesiones. |
| Chunking | 1 artículo = 1 chunk canónico | chunks por tokens | Preserva la unidad jurídica y permite citar artículo exacto. |
| Sesiones | Últimos N turnos | historial completo | Controla el contexto del modelo y la latencia. |

**Consecuencias:** todo el pipeline puede ejecutarse sin internet después de descargar modelos y fuentes. El hardware debe soportar el modelo elegido (≥16 GB RAM recomendados para 7B/8B; 3B es viable en CPU con 8–16 GB).

---

## 2026-10-20 — Fuentes y extracción (Pasos 5–6)

- **Decisión:** usar los PDF oficiales del SPIJ: Constitución 21.ª edición (dic. 2025) y Código Penal 12.ª edición.
- **Extracción:** `pdfplumber` con filtro por tamaño de fuente para descartar encabezados, pies, índices y notas al pie.
  - Constitución: `min_font=7.3`, desde la página 26.
  - Código Penal: `min_font=8.5`, desde la página 47.
- **Alternativas descartadas:** copiar texto de HTML (pierde estructura de títulos/capítulos) y OCR (los PDF tienen texto seleccionable).
- **Resultado:** `data/clean/constitucion.txt` (~135 577 caracteres) y `data/clean/codigo_penal.txt` (~357 450 caracteres).
- **Verificación:** hashes SHA-256 y URLs en `data/raw/FUENTES.md`.

---

## 2026-10-20 — Chunking legal (Pasos 7–8)

- **Decisión:** un artículo = un chunk canónico, con metadatos de libro, título, capítulo, sección, artículo, edición, fuente y fecha.
- **Regla de orden:** solo se aceptan artículos con numeración creciente; así se descartan referencias y notas al pie que hayan sobrevivido a la limpieza.
- **Casos especiales:** se conservan sufijos (`7-A`, `14-A`, `34-A`, `39-A`, `90-A`) y artículos del Título Preliminar con numeración romana (`I`–`X`).
- **Corte:** `TOPE_RE` detiene la lectura al llegar a `ÍNDICE`, `DISPOSICIONES FINALES/TRANSITORIAS/COMPLEMENTARIAS`, etc.
- **Resultado:** 211 chunks de Constitución (206 artículos + 5 con sufijo) y 575 del Código Penal (Título Preliminar I–X + 454 artículos base + 121 con sufijo; los artículos 262–269 no aparecen porque están derogados y el 270 figura como “DEROGADO”).
- **Validación:** `tests/validacion_dataset.md` (786 chunks, sin duplicados, campos completos, IDs válidos y orden creciente).

---

## 2026-10-20 — Embeddings e índice (Pasos 9–10)

- **Modelo:** `intfloat/multilingual-e5-base`, normalizado, prefijos `passage: ` para documentos y `query: ` para consultas.
- **Métrica:** L2 sobre vectores normalizados, equivalente a similitud coseno.
- **Persistencia:** ChromaDB en `db/`, colección `legislacion_pe` (786 chunks).
- **Limitación detectada:** e5 trunca a 512 tokens; el artículo 2 de la Constitución es muy largo y su embedding diluye incisos concretos.
- **Solución:** índice auxiliar de subchunks por inciso en `data/subchunks/` y colección `legislacion_pe_sub` (1 314 subchunks). Cada subchunk conserva `parent_id`; el retriever devuelve el artículo completo.
- **Alternativas descartadas:** aumentar `max_seq_length` (más costo y poca mejora), resumir artículos con un LLM (dependencia y riesgo de perder texto legal), buscar solo por palabras clave (peor recall semántico).

---

## 2026-10-20 — Recuperación híbrida (Paso 11)

- **Decisión:** combinar similitud semántica con una bonificación léxica:
  - `+0.12` si la consulta normalizada aparece completa en el texto;
  - `+0.05 × cobertura` de tokens de contenido.
- **Subchunks:** se consulta primero `legislacion_pe_sub`; se agrupa por `parent_id` y se conserva el mejor score. Luego se recupera el artículo completo desde `legislacion_pe`.
- **Fallback:** si la colección de subchunks no existe, se consulta directamente `legislacion_pe`.
- **Métricas de control (10 consultas, k=5):**
  - Solo artículos: Hit@1 50 %, Hit@5 80 %, MRR 0.650.
  - Con subchunks: Hit@1 50 %, Hit@5 100 %, MRR 0.733.
- **Lectura:** las confusiones de Hit@1 son artículos vecinos (p. ej. CP 169 vs. CONST 2 en libertad de expresión; CP 173 vs. CP 170 en violación sexual). El artículo correcto siempre queda dentro del contexto entregado al LLM.
- **Reporte:** `tests/retrieval_control.md`.

---

## 2026-10-20 — Diseño de citas y pipeline RAG (Paso 14)

- **Problema:** los modelos pequeños inventaban números de artículo o mezclaban documento y artículo al redactar la respuesta.
- **Decisión:** el contexto etiqueta cada fuente como `[S1]`, `[S2]`, `[S3]`. El prompt exige citar con esos identificadores y prohíbe que el modelo escriba números de artículo o una sección “Fuentes”.
- **Postproceso:** `rag_pipeline.py` reemplaza `[S#]` por `(Documento, Artículo N)`, elimina encabezados copiados y agrega una sección “Fuentes” verificable.
- **Verificación:** `citas_invalidas` detecta artículos citados que no existen en el contexto; `requiere_revision` se activa si hay citas inválidas o el texto es degenerado.
- **Fallback:** si el LLM devuelve texto degenerado, vacío o una respuesta en alcance sin citas, se entrega una respuesta extractiva con el artículo más relevante.
- **Compresión:** el contexto se limita a los 3 mejores artículos y, dentro de cada artículo largo, al inciso con mayor solapamiento con la consulta. Esto reduce ruido y latencia.

---

## 2026-10-20 — Evaluación de LLM (Paso 12)

Pruebas con `temperature=0.2`, `num_ctx=4096`, en CPU (sin GPU), 31.9 GB de RAM:

| Modelo | Precisión (0–5) | Cita correcta | Latencia (s) | Observaciones |
|---|---:|---|---:|---|
| `qwen2.5:7b` | 2 | No | 76–160 | Generó texto degenerado (`@@@@`, términos fuera de contexto, chino) y atribuyó el artículo 4 en lugar del artículo 2. |
| `qwen2.5:3b` | 4 | Sí, con postproceso | 23–67 | Coherente; acertó artículo 2 (libertad de expresión) y artículo 108 (homicidio calificado). Ocasionalmente agrega contexto adyacente y requiere el reemplazo de `[S#]`. |
| `llama3.1:8b` | — | — | — | Descarga lanzada; evaluación pendiente. |

- **Decisión para la demo:** `qwen2.5:3b` como modelo por defecto por estabilidad y latencia; `qwen2.5:7b` queda como opción si el equipo verifica que su hardware lo soporta.
- **Configuración:** `MJ_OLLAMA_MODEL=qwen2.5:3b`, `MJ_TEMPERATURE=0.2`, `MJ_NUM_CTX=4096`.
- **Limitación:** incluso con 3B, la latencia en CPU es de decenas de segundos; la demo debe ensayarse sin red y con tiempo de espera visible.

---

## 2026-10-20 — Guardrail de alcance

- Se agregó una regla léxica de alta precisión para consultas evidentemente
  laborales, civiles o tributarias: `CTS`, `gratificación`, `contrato de
  trabajo`, `despido`, `divorcio`, `pensión alimenticia`, `impuesto a la
  renta`, `IGV` y `SUNAT`.
- La respuesta devuelve `en_alcance=false`, `motivo="fuera_de_alcance"` y
  `modo="guardrail"`, sin ejecutar retrieval ni LLM.
- No se incluyen términos que también aparecen en el corpus penal
  (`testamento`, `herencia`, `sociedad anónima`) para no bloquear consultas
  válidas. B puede ampliar la lista en la capa de guardrails.

---

## Pendiente — Cierre de integración con B

- Validar el contrato JSON final (`respuesta`, `fuentes`, `citas_invalidas`, `requiere_revision`, `modo`, `latencia_s`) contra la API y la UI.
- Revisar el panel de transparencia con los campos de metadatos acordados.
- Completar la evaluación de `llama3.1:8b` si se decide usarlo.
- Ejecutar las 20–30 consultas de aceptación (Paso 22) y registrar resultados.
