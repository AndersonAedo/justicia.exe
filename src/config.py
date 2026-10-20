"""Configuración central de Mini-Juztina.

Todas las rutas son relativas a la raíz del proyecto y pueden sobreescribirse
con variables de entorno para facilitar pruebas y despliegues.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = Path(os.getenv("MJ_DATA_RAW", ROOT / "data" / "raw"))
DATA_CLEAN = Path(os.getenv("MJ_DATA_CLEAN", ROOT / "data" / "clean"))
DATA_CHUNKS = Path(os.getenv("MJ_DATA_CHUNKS", ROOT / "data" / "chunks"))
DB_DIR = Path(os.getenv("MJ_DB_DIR", ROOT / "db"))

COLLECTION = os.getenv("MJ_COLLECTION", "legislacion_pe")
SUBCOLLECTION = os.getenv("MJ_SUBCOLLECTION", f"{COLLECTION}_sub")
EMBED_MODEL = os.getenv("MJ_EMBED_MODEL", "intfloat/multilingual-e5-base")
EMBED_PREFIX_DOC = "passage: "
EMBED_PREFIX_QUERY = "query: "

OLLAMA_URL = os.getenv("MJ_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("MJ_OLLAMA_MODEL", "qwen2.5:3b")
LLM_TEMPERATURE = float(os.getenv("MJ_TEMPERATURE", "0.2"))
LLM_NUM_CTX = int(os.getenv("MJ_NUM_CTX", "4096"))
LLM_TIMEOUT = float(os.getenv("MJ_LLM_TIMEOUT", "180"))

TOP_K = int(os.getenv("MJ_TOP_K", "5"))
MAX_CONTEXT_CHARS = int(os.getenv("MJ_MAX_CONTEXT_CHARS", "10000"))

FECHA_DESCARGA = "2026-10-20"

DOCUMENTOS = {
    "constitucion": {
        "documento": "Constitución Política del Perú",
        "id_prefijo": "CONST",
        "fuente": "Ministerio de Justicia y Derechos Humanos (SPIJ)",
        "edicion": "Vigésima Primera Edición Oficial, diciembre 2025",
        "archivo": "constitucion_2025-12.pdf",
    },
    "codigo_penal": {
        "documento": "Código Penal",
        "id_prefijo": "CP",
        "fuente": "Ministerio de Justicia y Derechos Humanos (SPIJ)",
        "edicion": "Décimo Segunda Edición Oficial",
        "archivo": "codigo_penal_spij.pdf",
    },
}
