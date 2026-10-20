"""Paso 7-B: subchunks por inciso para mejorar la recuperación.

Los artículos largos (por ejemplo, el artículo 2 de la Constitución) diluyen su
embedding cuando se indexan completos. Este paso genera fragmentos de 300-700
caracteres con el encabezado del artículo repetido, y guarda el `parent_id`
para que el retriever devuelva siempre el artículo completo.

Uso:
    python -m src.build_subchunks
    python src/build_subchunks.py --input data/chunks --output data/subchunks
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_CHUNKS

MAX_CHARS = 700
MIN_CHARS = 120
CAMPOS_META = [
    "documento", "libro", "titulo", "capitulo", "seccion", "articulo",
    "fuente", "fecha", "edicion", "archivo", "tipo",
]
CORTE_INCISO = re.compile(
    r"(?=(?:\b\d{1,2}\.\s+(?:[A-ZÁÉÍÓÚÑ]))|(?:\b[a-z]\.\s+(?:[A-ZÁÉÍÓÚÑ])))"
)
CORTE_ORACION = re.compile(r"(?<=[.;:])\s+")


def normalizar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", texto)



def dividir_largo(texto: str, max_chars: int = MAX_CHARS) -> list[str]:
    if len(texto) <= max_chars:
        return [texto]
    oraciones = CORTE_ORACION.split(texto)
    salida: list[str] = []
    actual = ""
    for oracion in oraciones:
        if actual and len(actual) + 1 + len(oracion) > max_chars:
            salida.append(actual.strip())
            actual = oracion
        else:
            actual = f"{actual} {oracion}".strip()
    if actual:
        salida.append(actual.strip())
    return salida or [texto[:max_chars]]


def segmentar(chunk: dict, max_chars: int = MAX_CHARS) -> list[str]:
    texto = normalizar(chunk["texto"])
    partes = [p.strip() for p in CORTE_INCISO.split(texto) if p.strip()]
    if not partes:
        partes = [texto]

    encabezado = partes[0]
    if len(encabezado) > max_chars:
        return dividir_largo(texto, max_chars)
    if len(encabezado) < 40 and len(partes) > 1:
        encabezado = f"{partes[0]} {partes[1]}".strip()
        partes = [encabezado] + partes[2:]
    else:
        partes = [encabezado] + partes[1:]

    if len(partes) == 1:
        return dividir_largo(texto, max_chars)

    cuerpo: list[str] = []
    for parte in partes[1:]:
        if len(parte) < MIN_CHARS and cuerpo:
            cuerpo[-1] = f"{cuerpo[-1]} {parte}".strip()
        else:
            cuerpo.append(parte)

    salida: list[str] = []
    for parte in cuerpo:
        for trozo in dividir_largo(parte, max_chars):
            completo = normalizar(f"{encabezado} {trozo}")
            salida.extend(dividir_largo(completo, max_chars))
    return salida or [texto]


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera subchunks por inciso")
    parser.add_argument("--input", type=Path, default=DATA_CHUNKS)
    parser.add_argument(
        "--output", type=Path, default=DATA_CHUNKS.parent / "subchunks"
    )
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    args = parser.parse_args()

    rutas = sorted(args.input.glob("*.jsonl"))
    if not rutas:
        raise SystemExit(f"No hay JSONL en {args.input}")

    args.output.mkdir(parents=True, exist_ok=True)
    total = 0
    for ruta in rutas:
        salida: list[dict] = []
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            chunk = json.loads(linea)
            for indice, texto in enumerate(segmentar(chunk, args.max_chars), start=1):
                registro = {campo: chunk.get(campo, "") for campo in CAMPOS_META}
                registro.update(
                    {
                        "id": f"{chunk['id']}-s{indice:03d}",
                        "parent_id": chunk["id"],
                        "segmento": indice,
                        "texto": texto,
                        "orden": chunk.get("orden", 0),
                        "sufijo": chunk.get("sufijo", ""),
                    }
                )
                salida.append(registro)

        destino = args.output / ruta.name
        with destino.open("w", encoding="utf-8") as archivo:
            for registro in salida:
                archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        total += len(salida)
        print(f"{ruta.name}: {len(salida)} subchunks")

    print(f"[ok] {total} subchunks en {args.output}")


if __name__ == "__main__":
    main()
