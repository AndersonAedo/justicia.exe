# Reporte de pruebas RAG

Fecha: **2026-10-20**
Modelo: `qwen2.5:3b` (Ollama, CPU, `temperature=0.2`, `num_ctx=4096`)
Corpus: Constitución 21.ª ed. (dic. 2025) + Código Penal 12.ª ed.
Índice: `legislacion_pe` (786 artículos) + `legislacion_pe_sub` (1 314 subchunks)

## Resultados

| # | Consulta | Resultado esperado | Resultado obtenido | Latencia |
|---:|---|---|---|---:|
| 1 | ¿Qué protege la libertad de expresión? | Constitución, artículo 2 (inciso 4), con cita correcta | Cita el artículo 2; explica información, opinión, expresión y difusión; sin duplicados | 48 s |
| 2 | ¿Cuál es la pena por homicidio calificado? | Código Penal, artículo 108; pena no menor de 15 años | Cita artículo 108 y la pena no menor de 15 años | 38 s |
| 3 | ¿Cuánto me corresponde de CTS este año? | Fuera de alcance | Declina e indica que solo cubre Constitución y Código Penal | <1 s |
| 4 | ¿Qué dijo el TC en una sentencia de 2025 sobre el artículo 121? | Sin sustento (el corpus no incluye jurisprudencia) | “No encuentro sustento en las fuentes proporcionadas.” | 20 s |

## Observaciones

- La recuperación con subchunks coloca el artículo correcto en el top 5 en el
  100 % de las 10 consultas de control (`tests/retrieval_control.md`).
- El postproceso reemplaza `[S#]` por referencias verificables, elimina
  encabezados copiados y citas duplicadas; si el modelo escribe un número de
  artículo, se contrasta con las fuentes recuperadas.
- La latencia en CPU es de decenas de segundos; se recomienda calentar el modelo
  antes de la demo.
- El modelo 3B acierta el artículo y la pena en los casos probados, pero puede
  agregar artículos adyacentes; el panel de fuentes permite verificarlos.

## Reproducir

```powershell
python -m src.rag_pipeline "¿Qué protege la libertad de expresión?" --k 5 --modelo qwen2.5:3b --json
python -m src.rag_pipeline "¿Cuál es la pena por homicidio calificado?" --k 5 --modelo qwen2.5:3b --json
python -m src.rag_pipeline "¿Cuánto me corresponde de CTS este año?" --json
```
