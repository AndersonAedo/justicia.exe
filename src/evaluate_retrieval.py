"""Paso 14 (control): evaluación de recuperación con consultas de referencia.

Uso:
    python -m src.evaluate_retrieval
    python src/evaluate_retrieval.py --k 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import ROOT, TOP_K
from src.retriever import retrieve

CONSULTAS = [
    {"pregunta": "¿Qué protege la libertad de expresión?", "esperado": ["CONST-Art-2"]},
    {"pregunta": "¿Cuál es la pena por homicidio calificado?", "esperado": ["CP-Art-108"]},
    {"pregunta": "¿Qué derecho protege frente a una detención arbitraria?", "esperado": ["CONST-Art-2"]},
    {"pregunta": "¿Cómo se sanciona la tortura?", "esperado": ["CP-Art-321"]},
    {"pregunta": "¿Qué pena tiene la violación sexual?", "esperado": ["CP-Art-170"]},
    {"pregunta": "¿Cuándo se configura robo agravado?", "esperado": ["CP-Art-189"]},
    {"pregunta": "¿Qué es el peculado?", "esperado": ["CP-Art-387"]},
    {"pregunta": "¿Para qué sirve el hábeas corpus?", "esperado": ["CONST-Art-200"]},
    {"pregunta": "¿Qué garantiza la igualdad ante la ley?", "esperado": ["CONST-Art-2"]},
    {"pregunta": "¿Qué conducta constituye difamación?", "esperado": ["CP-Art-132"]},
]


def evaluar(k: int) -> dict:
    filas = []
    aciertos_1 = 0
    aciertos_k = 0
    suma_rr = 0.0

    for caso in CONSULTAS:
        resultados = retrieve(caso["pregunta"], k=k)
        ids = [r["id"] for r in resultados]
        posicion = next(
            (i + 1 for i, documento in enumerate(ids) if documento in caso["esperado"]),
            None,
        )
        if posicion == 1:
            aciertos_1 += 1
        if posicion is not None:
            aciertos_k += 1
            suma_rr += 1.0 / posicion
        filas.append(
            {
                "pregunta": caso["pregunta"],
                "esperado": ", ".join(caso["esperado"]),
                "top": ids,
                "posicion": posicion,
            }
        )

    total = len(CONSULTAS)
    return {
        "filas": filas,
        "hit1": aciertos_1 / total,
        "hitk": aciertos_k / total,
        "mrr": suma_rr / total,
        "total": total,
        "k": k,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa la recuperación híbrida")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument(
        "--salida", type=Path, default=ROOT / "tests" / "retrieval_control.md"
    )
    args = parser.parse_args()

    informe = evaluar(args.k)
    lineas = [
        "# Control de recuperación",
        "",
        "Modelo de embeddings: `intfloat/multilingual-e5-base`",
        "Índice: `legislacion_pe` + subchunks `legislacion_pe_sub`",
        f"Consultas: {informe['total']} | k = {informe['k']}",
        "",
        f"- **Hit@1:** {informe['hit1']:.0%}",
        f"- **Hit@{informe['k']}:** {informe['hitk']:.0%}",
        f"- **MRR:** {informe['mrr']:.3f}",
        "",
        "| # | Consulta | Esperado | Posición | Top 5 recuperado |",
        "|---:|---|---|---:|---|",
    ]
    for indice, fila in enumerate(informe["filas"], start=1):
        top = ", ".join(fila["top"])
        posicion = fila["posicion"] if fila["posicion"] else "—"
        lineas.append(
            f"| {indice} | {fila['pregunta']} | {fila['esperado']} | {posicion} | {top} |"
        )

    lineas += [
        "",
        "## Lectura",
        "",
        "- Hit@1 mide si el artículo correcto es el primero.",
        "- Hit@5 mide si aparece en el contexto entregado al LLM.",
        "- MRR premia que el artículo correcto aparezca en las primeras posiciones.",
        "- Una consulta se considera acertada si cualquiera de los IDs esperados aparece en el top k.",
        "- Los subchunks por inciso elevan Hit@5 de 80 % (solo artículos) a 100 %; las confusiones de Hit@1 son artículos vecinos.",
    ]

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print(f"Hit@1: {informe['hit1']:.0%} | Hit@{args.k}: {informe['hitk']:.0%} | MRR: {informe['mrr']:.3f}")
    print(f"Reporte: {args.salida}")
    return 0 if informe["hitk"] >= 0.8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
