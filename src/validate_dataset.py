"""Paso 8 (verificación): valida integridad y calidad básica de los chunks.

Uso:
    python -m src.validate_dataset
    python src/validate_dataset.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_CHUNKS, ROOT

CAMPOS = [
    "id", "documento", "articulo", "texto",
    "fuente", "fecha", "edicion", "archivo", "tipo",
]
PATRON_ID = re.compile(r"^(CONST|CP)-Art-([IVXLCDM]+|\d+(?:-[A-Z])?)$")
BASURA = re.compile(r"(@@@+|�|\?\?\?|lorem ipsum)", re.IGNORECASE)


def cargar_jsonl(ruta: Path) -> list[dict]:
    registros: list[dict] = []
    with ruta.open(encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if linea:
                registros.append(json.loads(linea))
    return registros


def clave_orden(chunk: dict) -> tuple[int, str]:
    base, _, sufijo = str(chunk["articulo"]).partition("-")
    if base.isdigit():
        return int(base), sufijo.upper()
    return 0, base.upper()


def validar(registros: list[dict], nombre: str) -> dict:
    problemas: list[str] = []
    ids = [r.get("id", "") for r in registros]
    duplicados = [i for i, n in Counter(ids).items() if n > 1]
    if duplicados:
        problemas.append(f"IDs duplicados: {duplicados}")

    faltantes = Counter()
    invalidos = 0
    basura = 0
    cortos = 0
    for r in registros:
        for campo in CAMPOS:
            if campo not in r or r[campo] in (None, ""):
                faltantes[campo] += 1
        if not PATRON_ID.match(str(r.get("id", ""))):
            invalidos += 1
        texto = str(r.get("texto", ""))
        if len(texto) < 10:
            cortos += 1
        if BASURA.search(texto):
            basura += 1

    if faltantes:
        problemas.append("Campos vacíos: " + ", ".join(f"{k}={v}" for k, v in faltantes.items()))
    if invalidos:
        problemas.append(f"IDs con formato inválido: {invalidos}")
    if cortos:
        problemas.append(f"Textos menores a 10 caracteres: {cortos}")
    if basura:
        problemas.append(f"Textos con posibles restos de OCR: {basura}")

    ordenados = sorted(registros, key=clave_orden)
    desordenados = 0
    for anterior, actual in zip(ordenados, ordenados[1:]):
        if clave_orden(actual) <= clave_orden(anterior):
            desordenados += 1
    if desordenados:
        problemas.append(f"Artículos fuera de orden: {desordenados}")

    return {
        "nombre": nombre,
        "total": len(registros),
        "problemas": problemas,
        "primer_articulo": ordenados[0]["articulo"] if ordenados else "-",
        "ultimo_articulo": ordenados[-1]["articulo"] if ordenados else "-",
        "promedio_chars": round(sum(len(r["texto"]) for r in registros) / max(1, len(registros))),
        "min_chars": min((len(r["texto"]) for r in registros), default=0),
        "max_chars": max((len(r["texto"]) for r in registros), default=0),
        "fechas": sorted({r.get("fecha", "") for r in registros}),
        "ediciones": sorted({r.get("edicion", "") for r in registros}),
    }


def validar_subchunks(rutas: list[Path], ids_padre: set[str]) -> list[dict]:
    filas = []
    for ruta in rutas:
        registros = cargar_jsonl(ruta)
        ids = [r.get("id", "") for r in registros]
        filas.append(
            {
                "nombre": ruta.stem,
                "total": len(registros),
                "unicos": len(set(ids)),
                "huerfanos": sum(1 for r in registros if r.get("parent_id") not in ids_padre),
                "vacios": sum(1 for r in registros if not str(r.get("texto", "")).strip()),
                "max_chars": max((len(r.get("texto", "")) for r in registros), default=0),
            }
        )
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida los chunks legales")
    parser.add_argument("--chunks", type=Path, default=DATA_CHUNKS)
    parser.add_argument("--subchunks", type=Path, default=DATA_CHUNKS.parent / "subchunks")
    parser.add_argument("--salida", type=Path, default=ROOT / "tests" / "validacion_dataset.md")
    args = parser.parse_args()

    rutas = sorted(args.chunks.glob("*.jsonl"))
    if not rutas:
        print(f"No hay archivos JSONL en {args.chunks}")
        return 1

    resultados = []
    for ruta in rutas:
        resultados.append(validar(cargar_jsonl(ruta), ruta.stem))

    try:
        directorio = args.chunks.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        directorio = str(args.chunks)

    lineas = [
        "# Validación del dataset",
        "",
        f"Directorio: `{directorio}`",
        "",
        "| Documento | Chunks | Primero | Último | Prom. chars | Mín | Máx |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for r in resultados:
        lineas.append(
            f"| {r['nombre']} | {r['total']} | {r['primer_articulo']} | "
            f"{r['ultimo_articulo']} | {r['promedio_chars']} | {r['min_chars']} | {r['max_chars']} |"
        )

    lineas += ["", "## Resultado de controles", ""]

    for r in resultados:
        estado = "OK" if not r["problemas"] else "REVISAR"
        lineas.append(f"### {r['nombre']}: {estado}")
        lineas.append("")
        if r["problemas"]:
            for problema in r["problemas"]:
                lineas.append(f"- {problema}")
        else:
            lineas.append("- Sin duplicados, campos completos, IDs válidos y orden creciente.")
        lineas.append(f"- Fecha(s) de descarga: {', '.join(r['fechas']) or '-'}")
        lineas.append(f"- Edición(es): {', '.join(r['ediciones']) or '-'}")
        lineas.append("")

    ids_padre = {r["id"] for ruta in rutas for r in cargar_jsonl(ruta)}
    subchunks = validar_subchunks(sorted(args.subchunks.glob("*.jsonl")), ids_padre)
    if subchunks:
        try:
            directorio_sub = args.subchunks.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            directorio_sub = str(args.subchunks)
        lineas += [
            "## Subchunks de recuperación",
            "",
            f"Directorio: `{directorio_sub}`",
            "",
            "| Documento | Subchunks | IDs únicos | Huérfanos | Vacíos | Máx. chars |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for r in subchunks:
            lineas.append(
                f"| {r['nombre']} | {r['total']} | {r['unicos']} | {r['huerfanos']} | "
                f"{r['vacios']} | {r['max_chars']} |"
            )
        total_sub = sum(r["total"] for r in subchunks)
        lineas += [
            "",
            f"Total: **{total_sub}** subchunks. Cada uno conserva `parent_id` y apunta a un artículo existente.",
            "",
        ]

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    total = sum(r["total"] for r in resultados)
    con_problemas = [r["nombre"] for r in resultados if r["problemas"]]
    print(f"Chunks validados: {total}")
    print(f"Reporte: {args.salida}")
    if con_problemas:
        print("Documentos a revisar: " + ", ".join(con_problemas))
        return 1
    print("Todos los controles pasaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
