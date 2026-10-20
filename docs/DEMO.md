# Guion de demostración en vivo — Mini-Juztina

**Objetivo:** demostrar el prototipo ejecutándose **offline**, evaluando precisión, citación de artículos y cumplimiento de guardrails.

**Duración:** 10–12 minutos + preguntas.
**Formato:** demo en vivo con el panel de transparencia visible.

---

## 1. Preparación (30 minutos antes)

- [ ] Equipo cargado y conectado a corriente.
- [ ] `ollama list` muestra el modelo elegido; hacer una consulta de calentamiento.
- [ ] Índice verificado: `python -c "import chromadb; ...; print(col.count())"`.
- [ ] API en http://localhost:8000/health con `status: ok`.
- [ ] UI abierta en http://localhost:8501, sesión limpia.
- [ ] PDFs oficiales abiertos en otra ventana para verificar citas en vivo.
- [ ] Capturas o video de respaldo de los 3 casos (por si falla el hardware).
- [ ] Cerrar aplicaciones que consuman RAM (navegadores extra, juegos, Docker innecesario).
- [ ] Notificaciones del sistema silenciadas.

**Prueba offline (mostrarla al inicio):**

1. Desconectar Wi-Fi / cable (o modo avión).
2. Mostrar que `localhost` sigue funcionando.
3. Ejecutar una consulta y comprobar que responde.
4. Mantener el equipo offline durante toda la demo.

---

## 2. Reparto durante la demo

| Persona | Rol en la demo |
|---|---|
| **A** | Explica las fuentes, el chunking y verifica la cita contra el PDF oficial. |
| **B** | Opera la UI/API, muestra el panel de transparencia y responde preguntas técnicas. |

---

## 3. Guion minuto a minuto

### 0:00–1:00 — Presentación

- Qué es Mini-Juztina: asistente legal local sobre Constitución y Código Penal peruanos.
- Qué NO es: no es asesoría legal personalizada.
- Promesa: toda respuesta cita documento + artículo + fragmento; si no hay sustento, lo dice.

### 1:00–2:30 — Arquitectura y privacidad

Mostrar el diagrama de `docs/ARQUITECTURA.md`:

`UI Streamlit → API FastAPI → RAG (retriever ChromaDB → prompt → Ollama) → respuesta + fuentes`

Mencionar: sin nube, sin API keys, sin envío de consultas a terceros; todo corre en el equipo.

### 2:30–5:30 — Caso 1: consulta dentro de alcance

**Consulta sugerida (verificar antes contra el texto descargado):**

> ¿Qué protege la libertad de expresión?

**Qué mostrar:**

1. Respuesta en lenguaje claro.
2. Cita: Constitución, artículo e inciso, con fragmento textual.
3. Panel de transparencia: documento, título, capítulo, artículo, fragmento y score.
4. Abrir el PDF oficial y contrastar el fragmento citado.
5. Señalar que el score y el `id` del chunk permiten rastrear la fuente.

**Mensaje clave:** la respuesta no sale "de la nada"; está anclada a un artículo recuperado.

### 5:30–7:30 — Caso 2: consulta fuera de alcance

**Consulta sugerida:**

> ¿Cuánto me corresponde de CTS este año?

**Qué mostrar:**

1. El asistente declina profesionalmente e indica que solo cubre Constitución y Código Penal.
2. No inventa una respuesta laboral.
3. La UI muestra el estado "fuera de alcance".

**Mensaje clave:** los guardrails limitan el dominio y evitan respuestas engañosas.

### 7:30–9:30 — Caso 3: consulta sin sustento en las fuentes

**Consulta sugerida (verificar que el corpus no la sustente):**

> ¿Qué dijo el Tribunal Constitucional en una sentencia de 2025 sobre el artículo 121 del Código Penal?

**Qué mostrar:**

1. Respuesta exacta: "No encuentro sustento en las fuentes proporcionadas."
2. Explicar que el corpus contiene la Constitución y el Código Penal, no jurisprudencia.
3. Si el modelo intenta responder, es un fallo: registrarlo y mostrar el ajuste del prompt (si ya está corregido, explicarlo).

**Mensaje clave:** el sistema prefiere no responder antes que alucinar.

### 9:30–11:00 — Panel de transparencia y métricas

- Mostrar 2–3 respuestas anteriores con sus fuentes y scores.
- Mencionar latencia media medida en `tests/report.md`.
- Explicar cómo se validó la cita contra el texto legal real.
- Mostrar `GET /health` y la prueba offline ya realizada.

### 11:00–12:00 — Cierre

- Limitaciones: solo dos documentos, no jurisprudencia, no asesoría personalizada.
- Trabajo futuro: ampliar corpus, filtros por artículo, evaluación automática.
- Invitar a preguntas.

---

## 4. Rúbrica de evaluación de la demo

| Criterio | Qué se observa | Aprobado si |
|---|---|---|
| Precisión | La respuesta coincide con el texto legal | 3/3 casos con respuesta correcta o declinación correcta |
| Citación | Documento + artículo + fragmento textual | Cita verificable en el PDF en el 100% de respuestas dentro de alcance |
| Guardrails | Fuera de alcance y sin sustento | Declina y no inventa en ambos casos |
| Transparencia | Panel con fuente y score | Visible y coherente con la respuesta |
| Offline | Sin red durante la demo | El flujo completo funciona |
| Claridad | Explicación y manejo del tiempo | Demo ≤ 12 min, preguntas respondidas |

Registrar el resultado en `tests/report.md` (fecha, modelo, versión del corpus, latencias y observaciones).

---

## 5. Plan de respaldo

| Falla | Acción |
|---|---|
| Ollama no responde | Reiniciar `ollama serve`; si falla, usar modelo 3B ya descargado. |
| API caída | Reiniciar `uvicorn`; mostrar `/health` y reintentar. |
| UI no carga | Abrir Swagger y hacer la consulta por API; mostrar el JSON con fuentes. |
| Respuesta lenta | Bajar `k` a 3; explicar la latencia esperada. |
| Fallo total | Reproducir el video/capturas de respaldo y continuar la explicación. |

---

## 6. Preguntas esperadas

- **¿Usan internet?** No; se muestra la prueba offline. Solo la instalación requirió red.
- **¿De dónde salen las respuestas?** De los artículos recuperados de ChromaDB y citados textualmente.
- **¿Qué pasa si la ley no está en el corpus?** El sistema declina o indica que no encuentra sustento.
- **¿Pueden añadir otras leyes?** Sí; se agregan PDFs, se reindexa y se amplía el alcance del prompt.
- **¿Es asesoría legal?** No; es una herramienta informativa y recomienda consultar a un abogado.
