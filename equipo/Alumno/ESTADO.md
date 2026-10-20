# Estado de Alumno (Rol A)

Actualizado: **2026-10-20**

## Resumen

| Área | Estado | Evidencia |
|---|---|---|
| Fuentes oficiales | Completado | `data/raw/FUENTES.md`, 2 PDF del SPIJ |
| Limpieza de texto | Completado | `data/clean/*.txt` |
| Chunking por artículo | Completado | `data/chunks/*.jsonl` (786 chunks) |
| Validación del corpus | Completado | `tests/validacion_dataset.md` (OK) |
| Embeddings + Chroma | Completado | `db/` colección `legislacion_pe` |
| Subchunks por inciso | Completado | `data/subchunks/*.jsonl` (1 314), colección `legislacion_pe_sub` |
| Recuperación híbrida | Completado | `src/retriever.py`, Hit@5 100 % |
| Pipeline RAG | Completado y probado | `src/rag_pipeline.py` |
| Contrato para B | Listo para integrar | JSON con `respuesta`, `fuentes`, `en_alcance`, `motivo`, `modo`, `citas_invalidas`, `requiere_revision` |
| Pruebas de aceptación 20–30 | Pendiente | Paso 22 |
| Demo sin red | Pendiente de ensayo final | `docs/DEMO.md` |

## Decisiones clave

- **Un artículo = un chunk canónico** con metadatos de libro, título, capítulo,
  sección, artículo, edición, fuente y fecha. Los sufijos (`108-A`, `108-B`,
  `46-A`, etc.) se indexan como artículos independientes.
- **Subchunks por inciso** para artículos largos: el artículo 2 de la
  Constitución se diluía en e5 (límite de 512 tokens). Cada subchunk guarda
  `parent_id` y el retriever devuelve el artículo completo.
- **Recuperación híbrida:** similitud semántica + bonificación léxica
  (`0.12` frase completa, `0.05 × cobertura`).
- **Citas verificables:** el prompt usa `[S1]`, `[S2]`, `[S3]`; el pipeline los
  reemplaza por `(Documento, Artículo N)` y agrega “Fuentes”.
- **Alcance:** una regla léxica de alta precisión declina consultas laborales,
  civiles o tributarias evidentes sin ejecutar retrieval ni LLM.
- **Modelo por defecto:** `qwen2.5:3b` por estabilidad y latencia en CPU;
  `qwen2.5:7b` queda como opción.

## Métricas de recuperación

10 consultas de control, `k=5`:

| Índice | Hit@1 | Hit@5 | MRR |
|---|---:|---:|---:|
| Solo artículos | 50 % | 80 % | 0.650 |
| Artículos + subchunks | 50 % | 100 % | 0.733 |

Las confusiones de Hit@1 son artículos vecinos; en las 10 consultas de control
el artículo correcto entra al contexto del LLM. Detalle en
`tests/retrieval_control.md`.

## Pruebas RAG realizadas (qwen2.5:3b, CPU)

| Consulta | Resultado | Latencia |
|---|---|---:|
| ¿Qué protege la libertad de expresión? | Cita Constitución, artículo 2 (inciso 4) | 48 s |
| ¿Cuál es la pena por homicidio calificado? | Cita Código Penal, artículo 108; pena no menor de 15 años | 38 s |
| ¿Cuánto me corresponde de CTS este año? | Declina: solo cubre Constitución y Código Penal | <1 s |
| ¿Qué dijo el TC en una sentencia de 2025 sobre el artículo 121? | “No encuentro sustento en las fuentes proporcionadas.” | 20 s |

## Pendientes

- [ ] Ejecutar las 20–30 consultas de aceptación (Paso 22) y registrar
  respuestas correctas, ambiguas y fuera de alcance.
- [ ] Revisar el contrato JSON con B y el panel de transparencia.
- [ ] Ensayar la demo completa sin red y registrar latencias finales.
- [ ] Evaluar `llama3.1:8b` si el equipo decide usarlo.
- [ ] Completar las secciones de datos/índice en el informe final.

## Riesgos conocidos

- La latencia en CPU es de decenas de segundos; la UI debe mostrar progreso.
- Los modelos pequeños pueden agregar contexto adyacente; el postproceso de
  citas y el fallback extractivo mitigan el riesgo.
- El corpus cubre solo Constitución y Código Penal; consultas de otras ramas
  deben declinarse.
