"""Paso 9-10: embeddings multilingües y base vectorial persistente.

Uso:
    python -m src.embedder --chunks data/chunks --persist db --collection legislacion_pe

El modelo se ejecuta localmente con sentence-transformers. Los vectores se
normalizan para que la distancia L2 de Chroma sea equivalente al ranking por
similitud coseno.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import (
    COLLECTION,
    DATA_CHUNKS,
    DB_DIR,
    EMBED_MODEL,
    EMBED_PREFIX_DOC,
)

METADATA_FIELDS = [
    "documento",
    "libro",
    "titulo",
    "capitulo",
    "seccion",
    "articulo",
    "fuente",
    "fecha",
    "edicion",
    "archivo",
    "tipo",
    "parent_id",
    "segmento",
]


def cargar_chunks(rutas: list[Path], limite: int | None = None) -> list[dict]:
    chunks: list[dict] = []
    for ruta in rutas:
        with ruta.open(encoding="utf-8") as fh:
            for linea in fh:
                if linea.strip():
                    chunks.append(json.loads(linea))
                    if limite and len(chunks) >= limite:
                        return chunks
    return chunks


def metadata_para_chroma(chunk: dict) -> dict:
    meta = {"chunk_id": chunk["id"]}
    for campo in METADATA_FIELDS:
        meta[campo] = str(chunk.get(campo, "") or "")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera embeddings y crea ChromaDB.")
    parser.add_argument("--chunks", type=Path, default=DATA_CHUNKS)
    parser.add_argument("--persist", type=Path, default=DB_DIR)
    parser.add_argument("--collection", default=COLLECTION)
    parser.add_argument("--model", default=EMBED_MODEL)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None, help="Solo para pruebas rápidas.")
    parser.add_argument("--no-reset", action="store_true", help="No borra la colección existente.")
    args = parser.parse_args()

    rutas = sorted(args.chunks.glob("*.jsonl"))
    if not rutas:
        raise SystemExit(f"No se encontraron JSONL en {args.chunks}")

    chunks = cargar_chunks(rutas, args.limit)
    if not chunks:
        raise SystemExit("No hay chunks para indexar")

    print(f"Cargando modelo local {args.model} (la primera vez puede descargar ~1 GB)...")
    modelo = SentenceTransformer(args.model, device=None)
    modelo.max_seq_length = 512

    textos = [EMBED_PREFIX_DOC + c["texto"] for c in chunks]
    print(f"Vectorizando {len(textos)} artículos en CPU/GPU disponible...")
    embeddings = modelo.encode(
        textos,
        batch_size=args.batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    args.persist.mkdir(parents=True, exist_ok=True)
    cliente = chromadb.PersistentClient(path=str(args.persist))

    if not args.no_reset:
        try:
            cliente.delete_collection(args.collection)
            print(f"Colección previa '{args.collection}' eliminada.")
        except Exception:
            pass

    coleccion = cliente.get_or_create_collection(
        name=args.collection,
        metadata={"descripcion": "Constitución y Código Penal del Perú"},
    )

    ids = [c["id"] for c in chunks]
    documentos = [c["texto"] for c in chunks]
    metadatas = [metadata_para_chroma(c) for c in chunks]
    lote = 64
    for inicio in range(0, len(ids), lote):
        fin = inicio + lote
        coleccion.add(
            ids=ids[inicio:fin],
            documents=documentos[inicio:fin],
            metadatas=metadatas[inicio:fin],
            embeddings=embeddings[inicio:fin].tolist(),
        )

    manifiesto = {
        "coleccion": args.collection,
        "modelo": args.model,
        "dimensión": int(embeddings.shape[1]),
        "chunks": len(chunks),
        "normalizado": True,
        "metrica": "L2 sobre vectores normalizados (equivale a coseno)",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "archivos": [r.name for r in rutas],
    }
    nombre_manifiesto = (
        "manifest.json" if args.collection == COLLECTION else f"manifest_{args.collection}.json"
    )
    (args.persist / nombre_manifiesto).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[ok] {coleccion.count()} chunks indexados en '{args.collection}' ({args.persist})")


if __name__ == "__main__":
    main()
