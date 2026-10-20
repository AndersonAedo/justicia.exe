# Fuentes oficiales

Registro de descargas usadas para construir el corpus. Fecha de descarga:
**2026-10-20**.

| Documento | Archivo | URL oficial | Páginas | SHA-256 | Verificado |
|---|---|---|---:|---|---|
| Constitución Política del Perú (21.ª ed. oficial, dic. 2025) | `constitucion_2025-12.pdf` | https://cdn.www.gob.pe/uploads/document/file/9139522/7498785-constitucion-politica_2025-final-dic-2025.pdf | 203 | `4FB083E4F8DBC1E9DEA9F52B5AA68FD322DBFD8E2136326C657D6D4499526E52` | [x] |
| Código Penal (12.ª ed. oficial) | `codigo_penal_spij.pdf` | https://spijweb.minjus.gob.pe/sdm_downloads/codigo-penal-decimo-segunda-edicion-oficial/ | 259 | `5938F7F8C13AE0BF73771FAE9AE503646B059DEA20A8E0B1BD839BFE950D669E` | [x] |

## Enlaces de descarga directa

- Constitución: `https://cdn.www.gob.pe/uploads/document/file/9139522/7498785-constitucion-politica_2025-final-dic-2025.pdf`
- Código Penal: `https://spijweb.minjus.gob.pe/?sdm_process_download=1&download_id=8709`
- Ficha del Código Penal: `https://spijweb.minjus.gob.pe/sdm_downloads/codigo-penal-decimo-segunda-edicion-oficial/`

## Criterios aplicados

- Se usó la versión oficial vigente a la fecha de descarga.
- Ambos PDF tienen texto seleccionable; no se aplicó OCR.
- La limpieza descarta encabezados, pies de página, índices y notas al pie
  mediante filtros de tamaño de fuente (`src/ingest.py`).
- El texto limpio resultante está en `data/clean/` y los chunks en
  `data/chunks/`.
- La numeración de artículos se validó contra el PDF; las ausencias detectadas
  (por ejemplo, artículos derogados) se documentan en
  `tests/validacion_dataset.md`.

## Verificación rápida

```powershell
Get-FileHash -Algorithm SHA256 data\raw\constitucion_2025-12.pdf, data\raw\codigo_penal_spij.pdf
```
