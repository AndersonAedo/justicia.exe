"""Paso 5-6: extracción y limpieza de los PDFs oficiales.

Uso:
    python -m src.ingest --input data/raw --output data/clean

El filtrado por tamaño de fuente elimina encabezados, pies de página y notas
al pie (que en estas ediciones usan cuerpos menores al texto principal). Así se
evita que las notas de "Texto anterior a la modificación" contaminen los chunks.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from pdfplumber import open as pdf_open

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_CLEAN, DATA_RAW

# Ajustes por edición: umbral de tamaño de fuente y página donde inicia el cuerpo.
PERFILES = {
    "constitucion": {"min_font": 7.3, "start_page": 26},
    "codigo_penal": {"min_font": 8.5, "start_page": 47},
}

LINEAS_IGNORADAS = {
    "CONSTITUCIÓN POLÍTICA DEL PERÚ",
    "MINISTERIO DE JUSTICIA Y DERECHOS HUMANOS",
    "CÓDIGO PENAL",
    "DECRETO LEGISLATIVO N° 635",
}


def clave_documento(nombre: str) -> str:
    bajo = unicodedata.normalize("NFKD", nombre.lower())
    bajo = "".join(c for c in bajo if not unicodedata.combining(c))
    if "constitucion" in bajo:
        return "constitucion"
    if "codigo" in bajo and "penal" in bajo:
        return "codigo_penal"
    raise ValueError(f"No se reconoce el documento: {nombre}")


def limpiar_lineas(texto: str) -> list[str]:
    lineas: list[str] = []
    for cruda in texto.splitlines():
        linea = cruda.replace("\u00a0", " ").replace("\u2009", " ").replace("\u200b", "")
        linea = re.sub(r"[ \t]+", " ", linea).strip()
        if not linea:
            continue
        if re.fullmatch(r"\d{1,3}", linea):
            continue
        if linea.upper() in LINEAS_IGNORADAS:
            continue
        lineas.append(linea)

    # Unir palabras cortadas al final de una línea (solo si continúa en minúscula).
    unidas: list[str] = []
    for linea in lineas:
        if unidas and unidas[-1].endswith("-") and re.match(r"^[a-záéíóúñü]", linea):
            unidas[-1] = unidas[-1][:-1] + linea
        else:
            unidas.append(linea)
    return unidas


def extraer_pdf(ruta: Path, min_font: float, start_page: int) -> str:
    paginas: list[str] = []
    with pdf_open(str(ruta)) as pdf:
        total = len(pdf.pages)
        for numero in range(start_page - 1, total):
            pagina = pdf.pages[numero]
            filtrada = pagina.filter(lambda obj: obj.get("size", 999) >= min_font)
            texto = filtrada.extract_text(x_tolerance=2, y_tolerance=3) or ""
            lineas = limpiar_lineas(texto)
            if lineas:
                paginas.append("\n".join(lineas))
    return "\n".join(paginas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae y limpia los PDFs oficiales.")
    parser.add_argument("--input", type=Path, default=DATA_RAW)
    parser.add_argument("--output", type=Path, default=DATA_CLEAN)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(args.input.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No se encontraron PDFs en {args.input}")

    for pdf in pdfs:
        clave = clave_documento(pdf.name)
        perfil = PERFILES[clave]
        texto = extraer_pdf(pdf, perfil["min_font"], perfil["start_page"])
        destino = args.output / f"{clave}.txt"
        destino.write_text(texto, encoding="utf-8")
        print(f"[ok] {pdf.name} -> {destino.name} ({len(texto):,} caracteres)")


if __name__ == "__main__":
    main()
