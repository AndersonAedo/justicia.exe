# Validación del dataset

Directorio: `data/chunks`

| Documento | Chunks | Primero | Último | Prom. chars | Mín | Máx |
|---|---:|---|---|---:|---:|---:|
| codigo_penal | 575 | I | 452 | 589 | 25 | 3187 |
| constitucion | 211 | 1 | 206 | 599 | 120 | 8904 |

## Resultado de controles

### codigo_penal: OK

- Sin duplicados, campos completos, IDs válidos y orden creciente.
- Fecha(s) de descarga: 2026-10-20
- Edición(es): Décimo Segunda Edición Oficial

### constitucion: OK

- Sin duplicados, campos completos, IDs válidos y orden creciente.
- Fecha(s) de descarga: 2026-10-20
- Edición(es): Vigésima Primera Edición Oficial, diciembre 2025

## Subchunks de recuperación

Directorio: `data/subchunks`

| Documento | Subchunks | IDs únicos | Huérfanos | Vacíos | Máx. chars |
|---|---:|---:|---:|---:|---:|
| codigo_penal | 964 | 964 | 0 | 0 | 803 |
| constitucion | 350 | 350 | 0 | 0 | 699 |

Total: **1314** subchunks. Cada uno conserva `parent_id` y apunta a un artículo existente.

