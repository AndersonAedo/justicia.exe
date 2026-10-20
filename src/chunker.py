"""Paso 7: chunking legal jerárquico (un artículo = un chunk).

Uso:
    python -m src.chunker --input data/clean --output data/chunks

El parser conserva Título, Capítulo, Libro y Sección, y detecta artículos con
numeración arábiga (1, 121, 108-A) o romana (I, II, X). Solo acepta artículos
en orden creciente para descartar referencias y notas al pie que hayan quedado
en el texto.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_CHUNKS, DATA_CLEAN, DOCUMENTOS, FECHA_DESCARGA

ARTICULO_RE = re.compile(
    r"^Art[íi]culo\s+([IVXLCDM]+|\d+)\s*[°º]?\s*(?:-\s*([A-Z]))?\s*"
    r"(?:[.\-–—]\s*)+(.*)$"
)
ENCABEZADO_RE = re.compile(
    r"^(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N)\s+"
    r"([IVXLCDM]+|\d+|[A-ZÁÉÍÓÚÑ]+)\b(.*)$"
)
TOPE_RE = re.compile(
    r"^(ÍNDICE|INDICE|TABLA DE CONTENIDO|NORMAS CONCORDADAS|"
    r"DISPOSICIONES\s+(FINALES|TRANSITORIAS|COMPLEMENTARIAS))\b",
    re.IGNORECASE,
)
ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_a_entero(valor: str) -> int:
    total = 0
    previo = 0
    for letra in reversed(valor.upper()):
        actual = ROMANOS[letra]
        total += -actual if actual < previo else actual
        previo = max(previo, actual)
    return total


def clave_documento(nombre: str) -> str:
    bajo = unicodedata.normalize("NFKD", nombre.lower())
    bajo = "".join(c for c in bajo if not unicodedata.combining(c))
    if "constitucion" in bajo:
        return "constitucion"
    if "codigo" in bajo and "penal" in bajo:
        return "codigo_penal"
    raise ValueError(f"No se reconoce el documento: {nombre}")


def orden_articulo(articulo: str) -> tuple[int, str]:
    base, _, sufijo = articulo.partition("-")
    if base.isdigit():
        return int(base), sufijo.upper()
    return roman_a_entero(base), sufijo.upper()


def es_encabezado(linea: str) -> re.Match[str] | None:
    if linea != linea.upper():
        return None
    return ENCABEZADO_RE.match(linea)


def etiqueta_encabezado(tipo: str, numero: str) -> str:
    if numero.isdigit():
        valor = numero
    elif numero and all(letra in ROMANOS for letra in numero.upper()):
        valor = numero.upper()
    else:
        valor = numero.title()
    return f"{tipo.title()} {valor}"


def mover_sumilla(buffer: list[str]) -> tuple[list[str], str]:
    """Separa una sumilla corta que quedó al final del artículo anterior."""
    sumilla: list[str] = []
    while len(buffer) > 1:
        ultima = buffer[-1].strip()
        if (
            len(ultima) <= 90
            and ultima
            and ultima[0].isupper()
            and not ultima[0].isdigit()
            and not ultima.endswith((".", ":", ";", "!", "?", ")"))
        ):
            sumilla.insert(0, buffer.pop())
        else:
            break
    return buffer, " ".join(sumilla)


def normalizar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", texto)


def procesar_documento(ruta: Path, clave: str) -> tuple[list[dict], dict]:
    meta = DOCUMENTOS[clave]
    lineas = ruta.read_text(encoding="utf-8").splitlines()

    chunks: list[dict] = []
    buffer: list[str] = []
    titulo = ""
    capitulo = ""
    libro = ""
    seccion = ""
    ultima_clave: tuple[int, str] = (0, "")
    ultimo_articulo = ""
    descartados = 0
    articulos_vistos: list[str] = []

    def cerrar() -> None:
        nonlocal buffer
        if not buffer or not ultimo_articulo:
            buffer = []
            return
        texto = normalizar(" ".join(buffer))
        if len(texto) >= 10:
            numero_orden, sufijo = orden_articulo(ultimo_articulo)
            chunks.append(
                {
                    "id": f"{meta['id_prefijo']}-Art-{ultimo_articulo}",
                    "documento": meta["documento"],
                    "libro": libro,
                    "titulo": titulo,
                    "capitulo": capitulo,
                    "seccion": seccion,
                    "articulo": ultimo_articulo,
                    "orden": numero_orden,
                    "sufijo": sufijo,
                    "texto": texto,
                    "fuente": meta["fuente"],
                    "fecha": FECHA_DESCARGA,
                    "edicion": meta["edicion"],
                    "archivo": meta["archivo"],
                    "tipo": clave,
                }
            )
        buffer = []

    for cruda in lineas:
        linea = cruda.strip()
        if not linea:
            continue

        if articulos_vistos and TOPE_RE.match(linea):
            cerrar()
            break

        encabezado = es_encabezado(linea)
        if encabezado and len(linea) <= 140:
            tipo, numero, _resto = encabezado.groups()
            etiqueta = etiqueta_encabezado(tipo, numero)
            if tipo == "LIBRO":
                libro = etiqueta
                ultima_clave = (0, "")
            elif tipo in ("TÍTULO", "TITULO"):
                titulo = etiqueta
                capitulo = ""
                seccion = ""
            elif tipo in ("CAPÍTULO", "CAPITULO"):
                capitulo = etiqueta
                seccion = ""
            else:
                seccion = etiqueta
            continue

        match = ARTICULO_RE.match(linea)
        if match:
            base = match.group(1).upper()
            sufijo = (match.group(2) or "").upper()
            articulo = f"{base}-{sufijo}" if sufijo else base
            clave_art = orden_articulo(articulo)
            if clave_art > ultima_clave:
                buffer, sumilla = mover_sumilla(buffer)
                cerrar()
                ultimo_articulo = articulo
                ultima_clave = clave_art
                articulos_vistos.append(articulo)
                buffer = ([sumilla] if sumilla else []) + [linea]
                continue
            descartados += 1
            if buffer:
                buffer.append(linea)
            continue

        if buffer:
            buffer.append(linea)

    cerrar()

    stats = {
        "documento": meta["documento"],
        "archivo": meta["archivo"],
        "chunks": len(chunks),
        "articulos_detectados": len(articulos_vistos),
        "duplicados_o_referencias_descartadas": descartados,
        "primer_articulo": articulos_vistos[0] if articulos_vistos else None,
        "ultimo_articulo": articulos_vistos[-1] if articulos_vistos else None,
        "libros": dict(Counter(c["libro"] for c in chunks if c["libro"])),
    }
    return chunks, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera chunks por artículo en JSONL.")
    parser.add_argument("--input", type=Path, default=DATA_CLEAN)
    parser.add_argument("--output", type=Path, default=DATA_CHUNKS)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    textos = sorted(args.input.glob("*.txt"))
    if not textos:
        raise SystemExit(f"No se encontraron textos limpios en {args.input}")

    stats_global: dict[str, dict] = {}
    for ruta in textos:
        clave = clave_documento(ruta.name)
        chunks, stats = procesar_documento(ruta, clave)
        destino = args.output / f"{clave}.jsonl"
        with destino.open("w", encoding="utf-8", newline="\n") as fh:
            for chunk in chunks:
                fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        stats_global[clave] = stats
        print(
            f"[ok] {ruta.name} -> {destino.name}: {len(chunks)} chunks "
            f"({stats['primer_articulo']}..{stats['ultimo_articulo']}, "
            f"{stats['duplicados_o_referencias_descartadas']} descartados)"
        )

    (args.output / "_stats.json").write_text(
        json.dumps(stats_global, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
