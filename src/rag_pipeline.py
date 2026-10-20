"""Paso 14: pipeline RAG local (retrieve → prompt → Ollama → JSON).

Uso:
    python -m src.rag_pipeline "¿Qué protege la libertad de expresión?" --k 5
    python -m src.rag_pipeline "..." --json

Diseño de citación:
- El contexto etiqueta cada fuente como [S1], [S2], ...
- El LLM solo escribe el identificador; el pipeline lo reemplaza por
  "Documento, Artículo N" y agrega la sección de fuentes con el fragmento exacto.
- Si el modelo devuelve una respuesta degenerada, se usa un extracto de la
  fuente principal como respaldo y se marca para revisión.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import (
    LLM_NUM_CTX,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    MAX_CONTEXT_CHARS,
    OLLAMA_MODEL,
    OLLAMA_URL,
    ROOT,
    TOP_K,
)
from src.retriever import STOPWORDS, normalizar_lexico, retrieve

SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system_prompt.txt"

NO_SUSTENTO = "no encuentro sustento en las fuentes"
FRASES_DECLINACION = (
    "solo cubro",
    "solo puedo responder",
    "fuera de alcance",
    "no puedo responder",
    "no corresponde a mi alcance",
    "no es posible responder",
)
TEMAS_FUERA_ALCANCE = {
    "cts": "CTS",
    "gratificacion": "gratificación",
    "contrato de trabajo": "contrato de trabajo",
    "despido": "despido",
    "divorcio": "divorcio",
    "pension alimenticia": "pensión alimenticia",
    "impuesto a la renta": "impuesto a la renta",
    "igv": "IGV",
    "sunat": "SUNAT",
}

SALUDOS = {
    "hola", "buenos dias", "buenas tardes", "buenas noches", "que tal",
    "como estas", "como va", "saludos", "hey", "hi", "hello",
    "gracias", "muchas gracias", "ok", "vale", "entendido",
    "adios", "chao", "hasta luego", "nos vemos",
}

CHITCHAT_PATTERNS = [
    r"^\s*hola\b", r"^\s*buenos?\s*(dias|tardes|noches)\b", r"^\s*que\s+tal\b",
    r"^\s*como\s+estas?\b", r"^\s*gracias\b", r"^\s*ok\b", r"^\s*vale\b",
    r"^\s*adios\b", r"^\s*chao\b", r"^\s*hasta\s+luego\b",
]


def es_saludo_o_chitchat(texto: str) -> bool:
    """Detecta si la entrada es un saludo o chitchat simple (no consulta legal)."""
    if not texto or not texto.strip():
        return False
    t = normalizar_lexico(texto)
    if t in SALUDOS:
        return True
    for pat in CHITCHAT_PATTERNS:
        if re.search(pat, t):
            return True
    # Muy corto y sin términos legales
    palabras = t.split()
    if len(palabras) <= 3:
        terminos_legales = {"articulo", "ley", "codigo", "constitucion", "pena", "delito",
                           "derecho", "articulo", "inciso", "norma", "sancion", "feminicidio",
                           "robo", "hurto", "homicidio", "violacion", "libertad", "expresion",
                           "violencia", "familiar", "sexual", "acoso", "hostigamiento",
                           "lesiones", "peculado", "cohecho", "tortura", "secuestro",
                           "extorsion", "fraude", "lavado", "asociacion", "ilicita",
                           "tenencia", "porte", "armas", "municiones", "explosivos",
                           "terrorismo", "rebelion", "sedicion", "traicion", "patria"}
        if not any(p in terminos_legales for p in palabras):
            return True
    return False


def cargar_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def segmentar(texto: str) -> list[str]:
    partes = re.split(r"(?=\b\d+\.\s)", texto)
    if len(partes) <= 1:
        partes = re.split(r"(?<=[.;:])\s+", texto)
    return [p.strip() for p in partes if p.strip()]


def relevancia(segmento: str, consulta: str) -> float:
    q = [t for t in normalizar_lexico(consulta).split() if len(t) > 2 and t not in STOPWORDS]
    if not q:
        return 0.0
    documento = normalizar_lexico(segmento)
    cobertura = sum(1 for t in q if t in documento) / len(q)
    exacta = 1.0 if normalizar_lexico(consulta) in documento else 0.0
    return cobertura + 0.5 * exacta


def comprimir_texto(texto: str, consulta: str, max_chars: int) -> str:
    """Selecciona el encabezado y los incisos más relevantes para la consulta."""
    if len(texto) <= max_chars:
        return texto
    segmentos = segmentar(texto)
    if len(segmentos) <= 1:
        return texto[:max_chars].rsplit(" ", 1)[0] + (" [...]" if len(texto) > max_chars else "")

    encabezado = segmentos[0]
    candidatos = segmentos[1:]
    mejor = max(candidatos, key=lambda s: relevancia(s, consulta))

    finales = [s for s in (encabezado, mejor) if s in segmentos]
    resultado = " ".join(finales)
    if len(resultado) > max_chars:
        resultado = resultado[:max_chars].rsplit(" ", 1)[0] + " [...]"
    return resultado


def construir_contexto(resultados: list[dict], consulta: str = "") -> str:
    if not resultados:
        return "(sin contexto recuperado)"

    por_fuente = max(700, MAX_CONTEXT_CHARS // max(1, len(resultados)))
    bloques: list[str] = ["FUENTES DISPONIBLES:"]
    for i, item in enumerate(resultados, 1):
        meta = item["metadatos"]
        bloques.append(
            f"S{i} = {meta.get('documento')}, Artículo {meta.get('articulo')}"
        )
    bloques.append("")

    for i, item in enumerate(resultados, 1):
        meta = item["metadatos"]
        encabezado = (
            f"[S{i}] {meta.get('documento')}, Artículo {meta.get('articulo')} "
            f"(Título: {meta.get('titulo')}; Capítulo: {meta.get('capitulo')})"
        )
        texto = comprimir_texto(item["texto"], consulta, por_fuente)
        bloques.append(f"{encabezado}\nTEXTO: {texto}")

    return "\n\n".join(bloques)[:MAX_CONTEXT_CHARS]


def construir_mensajes(
    pregunta: str,
    resultados: list[dict],
    historial: list[dict] | None = None,
) -> list[dict]:
    plantilla = cargar_system_prompt()
    system = plantilla.split("CONTEXTO:")[0].strip()
    contexto = construir_contexto(resultados, pregunta)

    if historial:
        turnos: list[str] = []
        for turno in historial[-3:]:
            turnos.append(f"Usuario: {turno.get('usuario', '')}")
            turnos.append(f"Asistente: {turno.get('asistente', '')}")
        contexto = "HISTORIAL RECIENTE:\n" + "\n".join(turnos) + "\n\n" + contexto

    user = f"CONTEXTO:\n{contexto}\n\nPREGUNTA:\n{pregunta}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def construir_prompt(
    pregunta: str,
    resultados: list[dict],
    historial: list[dict] | None = None,
) -> str:
    """Devuelve el prompt completo; útil para depuración."""
    mensajes = construir_mensajes(pregunta, resultados, historial)
    return mensajes[0]["content"] + "\n\n" + mensajes[1]["content"]


def consultar_ollama_libre(mensajes: list[dict], modelo: str = OLLAMA_MODEL) -> str:
    """Consulta al LLM sin contexto RAG (para saludos/chitchat)."""
    payload = {
        "model": modelo,
        "messages": mensajes,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 2048,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 300,
        },
    }
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as cliente:
            respuesta = cliente.post(f"{OLLAMA_URL}/api/chat", json=payload)
            respuesta.raise_for_status()
            datos = respuesta.json()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"No se pudo conectar con Ollama en {OLLAMA_URL}. "
            "Ejecuta 'ollama serve' y verifica el modelo con 'ollama list'."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            "Ollama no respondió a tiempo."
        ) from exc

    texto = ((datos.get("message") or {}).get("content") or "").strip()
    if not texto:
        raise RuntimeError("Ollama devolvió una respuesta vacía")
    return texto


def consultar_ollama(mensajes: list[dict], modelo: str = OLLAMA_MODEL) -> str:
    payload = {
        "model": modelo,
        "messages": mensajes,
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE,
            "num_ctx": LLM_NUM_CTX,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 500,
        },
    }
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as cliente:
            respuesta = cliente.post(f"{OLLAMA_URL}/api/chat", json=payload)
            respuesta.raise_for_status()
            datos = respuesta.json()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"No se pudo conectar con Ollama en {OLLAMA_URL}. "
            "Ejecuta 'ollama serve' y verifica el modelo con 'ollama list'."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            "Ollama no respondió a tiempo. Prueba con un modelo más pequeño "
            "o reduce el contexto recuperado."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Ollama devolvió un error: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Error de comunicación con Ollama: {exc}") from exc

    texto = ((datos.get("message") or {}).get("content") or "").strip()
    if not texto:
        raise RuntimeError("Ollama devolvió una respuesta vacía")
    return texto


def analizar_alcance(respuesta: str) -> tuple[bool, str]:
    bajo = respuesta.lower().strip()
    tiene_citas = bool(re.search(r"\[S\s*\d+\]|Art[íi]culo\s+\d", respuesta, re.I))
    if NO_SUSTENTO in bajo and (bajo.startswith(NO_SUSTENTO) or not tiene_citas):
        return False, "sin_sustento"
    for frase in FRASES_DECLINACION:
        if frase in bajo and (bajo.startswith(frase) or not tiene_citas):
            return False, "fuera_de_alcance"
    return True, "en_alcance"


def respuesta_valida(texto: str) -> bool:
    limpio = re.sub(r"\s+", " ", texto).strip()
    if len(limpio) < 25:
        return False
    if limpio.count("@") > 3:
        return False
    if re.search(r"[\u4e00-\u9fff]", limpio):
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{4,}", limpio):
        return False
    return len(set(limpio)) >= 8


def reemplazar_ids(respuesta: str, resultados: list[dict]) -> str:
    def reemplazo(match: re.Match[str]) -> str:
        indice = int(match.group(1))
        if 1 <= indice <= len(resultados):
            meta = resultados[indice - 1]["metadatos"]
            return f"({meta.get('documento')}, Artículo {meta.get('articulo')})"
        return "[fuente no disponible]"

    # Quitar una eventual sección "Fuentes" generada por el modelo.
    respuesta = re.split(r"\n\s*Fuentes\s*:", respuesta, maxsplit=1, flags=re.I)[0]
    respuesta = re.sub(r"\[S\s*(\d+)\]", reemplazo, respuesta).strip()
    # Quitar encabezados de contexto que el modelo haya copiado.
    respuesta = re.sub(
        r"\s*(?:Constitución Política del Perú|Código Penal),\s*Artículo\s*[\w-]+\s*\((?:Título|Capítulo)[^)]*\)",
        "",
        respuesta,
    )
    respuesta = re.sub(
        r"(\((?:Constitución Política del Perú|Código Penal),\s*Artículo\s*[\w-]+\))\s*"
        r"(?:Constitución Política del Perú|Código Penal),\s*Artículo\s*[\w-]+\.?",
        r"\1",
        respuesta,
    )
    respuesta = re.sub(
        r"(\([^()]*Artículo\s*[\w-]+\))(?:\s*\1)+",
        r"\1",
        respuesta,
    )
    return respuesta.strip()


def verificar_citas(respuesta: str, resultados: list[dict]) -> tuple[list[str], list[str]]:
    ids = {f"S{int(n)}" for n in re.findall(r"\[S\s*(\d+)\]", respuesta)}
    articulos = {
        c.upper()
        for c in re.findall(
            r"Art[íi]culos?\s+(\d+(?:-[A-Za-z])?|[IVXLCDM]+)", respuesta
        )
    }
    # Detectar menciones de documento (matching parcial por palabras clave)
    docs_en_respuesta = set()
    respuesta_lower = respuesta.lower()
    for item in resultados:
        doc = item["metadatos"].get("documento", "")
        if not doc:
            continue
        # Palabras clave del nombre del documento
        keywords = [w for w in doc.lower().split() if len(w) > 3]
        if any(kw in respuesta_lower for kw in keywords):
            docs_en_respuesta.add(doc)
    disponibles = {str(item["metadatos"].get("articulo", "")).upper() for item in resultados}
    citas_invalidas = sorted(articulos - disponibles)
    if ids:
        fuera = {i for i in ids if int(i[1:]) < 1 or int(i[1:]) > len(resultados)}
        citas_invalidas.extend(sorted(fuera))
    todas_citas = sorted(ids | articulos | docs_en_respuesta)
    return todas_citas, sorted(set(citas_invalidas))


def formatear_fuentes(resultados: list[dict], max_fragmento: int = 500) -> list[dict]:
    fuentes: list[dict] = []
    for item in resultados:
        meta = item["metadatos"]
        fragmento = item["texto"]
        if len(fragmento) > max_fragmento:
            fragmento = fragmento[:max_fragmento].rsplit(" ", 1)[0] + " [...]"
        fuentes.append(
            {
                "id": item["id"],
                "documento": meta.get("documento", ""),
                "titulo": meta.get("titulo", ""),
                "capitulo": meta.get("capitulo", ""),
                "articulo": meta.get("articulo", ""),
                "fragmento": fragmento,
                "score": item["score"],
            }
        )
    return fuentes


def agregar_fuentes(respuesta: str, fuentes: list[dict], max_fuentes: int = 3) -> str:
    lineas = ["", "Fuentes:"]
    for fuente in fuentes[:max_fuentes]:
        lineas.append(
            f'- {fuente["documento"]}, Artículo {fuente["articulo"]}: '
            f'"{fuente["fragmento"]}"'
        )
    return respuesta.rstrip() + "\n" + "\n".join(lineas)


def respuesta_extractiva(fuentes: list[dict]) -> str:
    principal = fuentes[0]
    return (
        f'Según {principal["documento"]}, Artículo {principal["articulo"]}: '
        f'"{principal["fragmento"]}"'
    )


def detectar_consulta_amplia(pregunta: str, resultados: list[dict]) -> bool:
    """Detecta si la consulta es muy amplia (pocas palabras, términos generales)."""
    if not resultados:
        return False
    palabras = pregunta.strip().split()
    if len(palabras) <= 3:
        # Verificar si los resultados son diversos (diferentes artículos/delitos)
        articulos = {r["metadatos"].get("articulo") for r in resultados}
        if len(articulos) >= 3:
            return True
    return False


def sugerir_temas(resultados: list[dict], max_sugerencias: int = 5) -> str:
    """Genera sugerencias basadas en los artículos recuperados."""
    if not resultados:
        return ""
    
    # Agrupar por tema/delito usando palabras clave del texto
    sugerencias = []
    vistos = set()
    
    for r in resultados[:max_sugerencias]:
        art = r["metadatos"].get("articulo", "")
        doc = r["metadatos"].get("documento", "")
        texto = r["texto"][:200].lower()
        
        # Extraer tema principal del artículo
        if "feminicidio" in texto and "feminicidio" not in vistos:
            sugerencias.append(f"• Feminicidio (Art. {art} {doc})")
            vistos.add("feminicidio")
        elif "violación sexual" in texto and "violación sexual" not in vistos:
            sugerencias.append(f"• Violación sexual (Art. {art} {doc})")
            vistos.add("violación sexual")
        elif "violencia familiar" in texto and "violencia familiar" not in vistos:
            sugerencias.append(f"• Violencia familiar (Art. {art} {doc})")
            vistos.add("violencia familiar")
        elif "acoso sexual" in texto and "acoso sexual" not in vistos:
            sugerencias.append(f"• Acoso/hostigamiento sexual (Art. {art} {doc})")
            vistos.add("acoso sexual")
        elif "lesiones" in texto and "lesiones" not in vistos:
            sugerencias.append(f"• Lesiones (Art. {art} {doc})")
            vistos.add("lesiones")
        elif "libertad de expresión" in texto or "libertad de informaci" in texto:
            if "libertad de expresión" not in vistos:
                sugerencias.append(f"• Libertad de expresión (Art. {art} {doc})")
                vistos.add("libertad de expresión")
        elif "homicidio" in texto and "homicidio" not in vistos:
            sugerencias.append(f"• Homicidio (Art. {art} {doc})")
            vistos.add("homicidio")
        elif "robo" in texto and "robo" not in vistos:
            sugerencias.append(f"• Robo/hurto (Art. {art} {doc})")
            vistos.add("robo")
        elif "peculado" in texto and "peculado" not in vistos:
            sugerencias.append(f"• Peculado/cohecho (Art. {art} {doc})")
            vistos.add("peculado")
        elif "tortura" in texto and "tortura" not in vistos:
            sugerencias.append(f"• Tortura (Art. {art} {doc})")
            vistos.add("tortura")
    
    if not sugerencias:
        # Fallback: mostrar los primeros artículos
        for r in resultados[:3]:
            art = r["metadatos"].get("articulo", "")
            doc = r["metadatos"].get("documento", "")
            sugerencias.append(f"• Artículo {art} {doc}")
    
    if sugerencias:
        intro = "Tu consulta es amplia. Estos son los temas relacionados que encuentro en la normativa:\n\n"
        return intro + "\n".join(sugerencias[:max_sugerencias]) + "\n\nPregúntame sobre uno específico (ej: «¿Qué pena tiene el feminicidio?»)."
    return ""


def detectar_fuera_alcance(pregunta: str) -> str:
    consulta = normalizar_lexico(pregunta)
    for tema in TEMAS_FUERA_ALCANCE:
        if tema in consulta:
            return tema
    return ""


def respuesta_fuera_alcance(tema: str) -> str:
    etiqueta = TEMAS_FUERA_ALCANCE.get(tema, tema)
    return (
        "Esta consulta está fuera de mi alcance: solo cubro la Constitución "
        "Política del Perú y el Código Penal peruano. "
        f"El tema detectado ({etiqueta}) corresponde a otra rama del derecho; "
        "para un caso concreto consulta a un especialista."
    )


def responder(
    pregunta: str,
    k: int = TOP_K,
    historial: list[dict] | None = None,
    usar_llm: bool = True,
    modelo: str = OLLAMA_MODEL,
    modo_hibrido: bool = True,
) -> dict:
    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta está vacía")

    inicio = time.perf_counter()

    # MODO HÍBRIDO: saludos/chitchat → LLM libre (sin RAG)
    if modo_hibrido and es_saludo_o_chitchat(pregunta):
        try:
            mensajes = [
                {"role": "system", "content": "Eres Mini-Juztina, un asistente legal amable. Responde breve y cordial. Si te preguntan por temas legales, indica que puedes ayudar con la Constitución y el Código Penal."},
                {"role": "user", "content": pregunta},
            ]
            if historial:
                # Incluir último turno de contexto para continuidad
                for h in historial[-2:]:
                    mensajes.insert(-1, {"role": "user", "content": h.get("usuario", "")})
                    mensajes.insert(-1, {"role": "assistant", "content": h.get("asistente", "")})
            
            respuesta_libre = consultar_ollama_libre(mensajes, modelo=modelo)
            return {
                "pregunta": pregunta,
                "respuesta": respuesta_libre,
                "fuentes": [],
                "en_alcance": True,
                "motivo": "saludo_chitchat",
                "modo": "hibrido_libre",
                "advertencia": "",
                "citas_detectadas": [],
                "citas_invalidas": [],
                "requiere_revision": False,
                "modelo": modelo,
                "k": 0,
                "latencia_s": round(time.perf_counter() - inicio, 2),
            }
        except RuntimeError as exc:
            # Si falla el LLM libre, continuar con RAG normal
            pass

    tema = detectar_fuera_alcance(pregunta)
    if tema:
        return {
            "pregunta": pregunta,
            "respuesta": respuesta_fuera_alcance(tema),
            "fuentes": [],
            "en_alcance": False,
            "motivo": "fuera_de_alcance",
            "modo": "guardrail",
            "advertencia": "",
            "citas_detectadas": [],
            "citas_invalidas": [],
            "requiere_revision": False,
            "modelo": "guardrail",
            "k": k,
            "latencia_s": round(time.perf_counter() - inicio, 2),
        }

    resultados = retrieve(pregunta, k=k)
    fuentes = formatear_fuentes(resultados)
    resultados_prompt = resultados[:3]

    modo = "llm"
    advertencia = ""
    if usar_llm:
        mensajes = construir_mensajes(pregunta, resultados_prompt, historial)
        error_llm = ""
        try:
            respuesta_llm = consultar_ollama(mensajes, modelo=modelo)
        except RuntimeError as exc:
            respuesta_llm = ""
            error_llm = str(exc)
        en_alcance, motivo = analizar_alcance(respuesta_llm)
        citas, citas_invalidas = verificar_citas(respuesta_llm, resultados_prompt)

        # Caso: consulta amplia sin respuesta específica pero con artículos relevantes
        if motivo == "sin_sustento" and detectar_consulta_amplia(pregunta, resultados):
            sugerencias = sugerir_temas(resultados)
            if sugerencias:
                respuesta = sugerencias
                en_alcance = True
                modo = "sugerencias"
                motivo = "consulta_amplia"
                advertencia = "Consulta amplia detectada; se muestran temas sugeridos."
            else:
                modo = "fallback_extractivo"
                respuesta = respuesta_extractiva(fuentes)
                en_alcance = True
                motivo = "fallback_extractivo"
                advertencia = error_llm or "El modelo no produjo una respuesta válida."
        elif not respuesta_valida(respuesta_llm) or (motivo == "en_alcance" and not citas):
            modo = "fallback_extractivo"
            respuesta = respuesta_extractiva(fuentes)
            en_alcance = True
            motivo = "fallback_extractivo"
            advertencia = error_llm or (
                "El modelo no produjo una respuesta válida; "
                "se muestra un extracto de la fuente principal."
            )
        else:
            respuesta = reemplazar_ids(respuesta_llm, resultados_prompt)
            if en_alcance:
                respuesta = agregar_fuentes(respuesta, fuentes)
    else:
        respuesta = (
            "Modo sin LLM: se recuperaron los siguientes artículos como contexto.\n\n"
            + construir_contexto(resultados, pregunta)
        )
        en_alcance, motivo = True, "sin_llm"
        citas, citas_invalidas = [], []
        modo = "sin_llm"

    latencia = round(time.perf_counter() - inicio, 2)
    return {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "fuentes": fuentes,
        "en_alcance": en_alcance,
        "motivo": motivo,
        "modo": modo,
        "advertencia": advertencia,
        "citas_detectadas": citas,
        "citas_invalidas": citas_invalidas,
        "requiere_revision": bool(citas_invalidas) or modo == "fallback_extractivo",
        "modelo": modelo if usar_llm else "sin_llm",
        "k": k,
        "latencia_s": latencia,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline RAG local.")
    parser.add_argument("pregunta", help="Consulta en lenguaje natural")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--modelo", default=OLLAMA_MODEL)
    parser.add_argument("--sin-llm", action="store_true", help="Solo recupera contexto.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON completo")
    args = parser.parse_args()

    try:
        salida = responder(
            args.pregunta,
            k=args.k,
            usar_llm=not args.sin_llm,
            modelo=args.modelo,
        )
    except RuntimeError as exc:
        raise SystemExit(f"[error] {exc}") from exc

    if args.json:
        print(json.dumps(salida, ensure_ascii=False, indent=2))
        return

    print(salida["respuesta"])
    if salida["advertencia"]:
        print(f"\n[aviso] {salida['advertencia']}")
    print("\n--- Fuentes recuperadas ---")
    for fuente in salida["fuentes"]:
        print(
            f"- {fuente['documento']}, Artículo {fuente['articulo']} "
            f"(score {fuente['score']:.3f})"
        )
    print(
        f"\nAlcance: {salida['motivo']} | Modo: {salida['modo']} | "
        f"Latencia: {salida['latencia_s']} s"
    )


if __name__ == "__main__":
    main()
