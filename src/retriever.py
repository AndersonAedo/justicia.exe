"""Paso 11: recuperación semántica sobre la colección legal.

Uso:
    python -m src.retriever "homicidio calificado" --k 5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import (
    COLLECTION,
    DB_DIR,
    EMBED_MODEL,
    EMBED_PREFIX_QUERY,
    SUBCOLLECTION,
    TOP_K,
)


@lru_cache(maxsize=1)
def cargar_modelo(nombre: str = EMBED_MODEL) -> SentenceTransformer:
    modelo = SentenceTransformer(nombre, device=None)
    modelo.max_seq_length = 512
    return modelo


@lru_cache(maxsize=4)
def cargar_coleccion(persist: str = str(DB_DIR), nombre: str = COLLECTION):
    cliente = chromadb.PersistentClient(path=persist)
    try:
        return cliente.get_collection(nombre)
    except Exception as exc:
        raise RuntimeError(
            f"No existe la colección '{nombre}' en '{persist}'. "
            "Ejecuta primero: python -m src.embedder"
        ) from exc


def distancia_a_score(distancia: float) -> float:
    """Convierte L2 al cuadrado sobre vectores normalizados a similitud coseno."""
    return max(0.0, min(1.0, 1.0 - (float(distancia) / 2.0)))


STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "que", "en", "y", "a", "al", "del", "por", "con", "para",
    "se", "su", "sus", "es", "son", "como", "sobre", "the", "of",
}


def normalizar_lexico(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def bonificacion_lexica(query: str, texto: str) -> float:
    consulta = normalizar_lexico(query)
    documento = normalizar_lexico(texto)
    if not consulta:
        return 0.0
    exacta = 1.0 if consulta in documento else 0.0
    tokens = [t for t in consulta.split() if len(t) > 2 and t not in STOPWORDS]
    cobertura = (
        sum(1 for t in tokens if t in documento) / len(tokens) if tokens else 0.0
    )
    return 0.12 * exacta + 0.05 * cobertura


def _consultar(coleccion, vector: list[float], n: int) -> list[tuple]:
    resultado = coleccion.query(
        query_embeddings=[vector],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    ids = resultado.get("ids", [[]])[0]
    documentos = resultado.get("documents", [[]])[0]
    metadatos = resultado.get("metadatas", [[]])[0]
    distancias = resultado.get("distances", [[]])[0]
    return list(zip(ids, documentos, metadatos, distancias))


def _item(chunk_id: str, texto: str, meta: dict, score: float, semantico: float, distancia: float) -> dict:
    return {
        "id": chunk_id,
        "texto": texto,
        "metadatos": meta,
        "score": round(score, 4),
        "score_semantico": round(semantico, 4),
        "distancia": round(float(distancia), 4),
    }


def retrieve(
    query: str,
    k: int = TOP_K,
    persist_dir: str | Path = DB_DIR,
    collection_name: str = COLLECTION,
    subcollection_name: str = SUBCOLLECTION,
) -> list[dict]:
    if not query or not query.strip():
        raise ValueError("La consulta está vacía")

    modelo = cargar_modelo()
    vector = modelo.encode(
        EMBED_PREFIX_QUERY + query.strip(),
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    coleccion = cargar_coleccion(str(persist_dir), collection_name)
    if coleccion.count() == 0:
        raise RuntimeError("La colección está vacía. Ejecuta primero: python -m src.embedder")

    subcoleccion = None
    if subcollection_name:
        try:
            subcoleccion = cargar_coleccion(str(persist_dir), subcollection_name)
        except RuntimeError:
            subcoleccion = None

    if subcoleccion is not None and subcoleccion.count() > 0:
        candidatos = min(max(k * 8, 40), subcoleccion.count())
        hijos = _consultar(subcoleccion, vector, candidatos)
        mejores: dict[str, dict] = {}
        for hijo_id, hijo_texto, meta, distancia in hijos:
            padre = str(meta.get("parent_id") or hijo_id)
            semantico = distancia_a_score(distancia)
            final = min(1.0, semantico + bonificacion_lexica(query, hijo_texto))
            if padre not in mejores or final > mejores[padre]["score"]:
                mejores[padre] = {
                    "score": final,
                    "semantico": semantico,
                    "distancia": distancia,
                    "match_id": hijo_id,
                }

        ids = list(mejores)
        padres = coleccion.get(ids=ids, include=["documents", "metadatas"])
        textos = dict(zip(padres.get("ids", []), padres.get("documents", [])))
        metadatos = dict(zip(padres.get("ids", []), padres.get("metadatas", [])))

        salida = []
        for padre, datos in mejores.items():
            if padre not in textos:
                continue
            item = _item(
                padre,
                textos[padre],
                metadatos.get(padre, {}),
                datos["score"],
                datos["semantico"],
                datos["distancia"],
            )
            item["match_id"] = datos["match_id"]
            salida.append(item)
        salida.sort(key=lambda item: item["score"], reverse=True)
        return salida[:k]

    candidatos = min(max(k * 4, 20), max(1, coleccion.count()))
    salida = []
    for chunk_id, texto, meta, distancia in _consultar(coleccion, vector, candidatos):
        semantico = distancia_a_score(distancia)
        final = min(1.0, semantico + bonificacion_lexica(query, texto))
        salida.append(_item(chunk_id, texto, meta, final, semantico, distancia))

    salida.sort(key=lambda item: item["score"], reverse=True)
    return salida[:k]

def main() -> None:
    parser = argparse.ArgumentParser(description="Recupera artículos relevantes.")
    parser.add_argument("consulta", help="Consulta en lenguaje natural")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--subcollection", default=SUBCOLLECTION, help="Colección de subchunks")
    parser.add_argument("--json", action="store_true", help="Imprime JSON completo")
    args = parser.parse_args()

    resultados = retrieve(args.consulta, k=args.k, subcollection_name=args.subcollection)
    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
        return

    print(f"Consulta: {args.consulta}\n")
    for i, item in enumerate(resultados, 1):
        meta = item["metadatos"]
        print(
            f"{i}. {meta.get('documento')} — Artículo {meta.get('articulo')} "
            f"(score {item['score']:.3f})"
        )
        print(f"   {item['texto'][:260]}...\n")


if __name__ == "__main__":
    main()
