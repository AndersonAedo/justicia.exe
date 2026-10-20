# Control de recuperación

Modelo de embeddings: `intfloat/multilingual-e5-base`
Índice: `legislacion_pe` + subchunks `legislacion_pe_sub`
Consultas: 10 | k = 5

- **Hit@1:** 50%
- **Hit@5:** 100%
- **MRR:** 0.733

| # | Consulta | Esperado | Posición | Top 5 recuperado |
|---:|---|---|---:|---|
| 1 | ¿Qué protege la libertad de expresión? | CONST-Art-2 | 2 | CP-Art-169, CONST-Art-2, CONST-Art-61, CP-Art-220, CP-Art-217 |
| 2 | ¿Cuál es la pena por homicidio calificado? | CP-Art-108 | 1 | CP-Art-108, CP-Art-108-A, CP-Art-109, CP-Art-112, CP-Art-111 |
| 3 | ¿Qué derecho protege frente a una detención arbitraria? | CONST-Art-2 | 3 | CONST-Art-27, CONST-Art-139, CONST-Art-2, CP-Art-417, CP-Art-419 |
| 4 | ¿Cómo se sanciona la tortura? | CP-Art-321 | 1 | CP-Art-321, CP-Art-315, CP-Art-415, CP-Art-409-A, CP-Art-417-A |
| 5 | ¿Qué pena tiene la violación sexual? | CP-Art-170 | 2 | CP-Art-173, CP-Art-170, CP-Art-173-A, CP-Art-171, CP-Art-172 |
| 6 | ¿Cuándo se configura robo agravado? | CP-Art-189 | 1 | CP-Art-189, CP-Art-186, CP-Art-195, CP-Art-196-A, CP-Art-307-B |
| 7 | ¿Qué es el peculado? | CP-Art-387 | 1 | CP-Art-387, CP-Art-388, CP-Art-291, CP-Art-25, CP-Art-219 |
| 8 | ¿Para qué sirve el hábeas corpus? | CONST-Art-200 | 2 | CONST-Art-202, CONST-Art-200, CONST-Art-183, CP-Art-157, CP-Art-I |
| 9 | ¿Qué garantiza la igualdad ante la ley? | CONST-Art-2 | 1 | CONST-Art-2, CP-Art-10, CONST-Art-26, CONST-Art-62, CONST-Art-51 |
| 10 | ¿Qué conducta constituye difamación? | CP-Art-132 | 2 | CP-Art-133, CP-Art-132, CP-Art-136, CP-Art-130, CP-Art-138 |

## Lectura

- Hit@1 mide si el artículo correcto es el primero.
- Hit@5 mide si aparece en el contexto entregado al LLM.
- MRR premia que el artículo correcto aparezca en las primeras posiciones.
- Una consulta se considera acertada si cualquiera de los IDs esperados aparece en el top k.
- Los subchunks por inciso elevan Hit@5 de 80 % (solo artículos) a 100 %; las confusiones de Hit@1 son artículos vecinos.
