"""Interfaz Streamlit de Mini-Juztina (rol B).

Consume la API local y muestra, además de la respuesta, el panel de
transparencia con las fuentes y los metadatos que produce el pipeline de A.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
import streamlit as st

API_URL = os.getenv("MJ_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_CHAT = 240.0
TIMEOUT_CORTO = 5.0

st.set_page_config(page_title="Mini-Juztina", layout="wide")


@st.cache_data(ttl=10, show_spinner=False)
def _salud() -> dict[str, Any]:
    try:
        respuesta = httpx.get(f"{API_URL}/health", timeout=TIMEOUT_CORTO)
        respuesta.raise_for_status()
        return respuesta.json()
    except Exception as exc:
        return {"error": str(exc)}


def _cargar_historial(sesion_id: str) -> list[dict[str, Any]]:
    try:
        respuesta = httpx.get(
            f"{API_URL}/sesiones/{sesion_id}/historial",
            params={"limite": 50},
            timeout=TIMEOUT_CORTO,
        )
        respuesta.raise_for_status()
        turnos = respuesta.json().get("turnos", [])
    except Exception:
        return []

    mensajes: list[dict[str, Any]] = []
    for turno in turnos:
        mensajes.append(
            {
                "role": turno.get("rol", "assistant"),
                "content": turno.get("contenido", ""),
                "meta": turno if turno.get("rol") == "assistant" else None,
            }
        )
    return mensajes


def _nueva_sesion() -> str:
    return uuid.uuid4().hex


def _formatear_score(valor: Any) -> str:
    try:
        return f"{float(valor):.3f}"
    except (TypeError, ValueError):
        return "n/d"


def _enviar_consulta(mensaje: str) -> dict[str, Any]:
    respuesta = httpx.post(
        f"{API_URL}/chat",
        json={"mensaje": mensaje, "sesion_id": st.session_state.sesion_id},
        timeout=TIMEOUT_CHAT,
    )
    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("detail", respuesta.text)
        except ValueError:
            detalle = respuesta.text
        raise RuntimeError(str(detalle))
    return respuesta.json()


def _mostrar_fuentes(fuentes: list[dict[str, Any]]) -> None:
    if not fuentes:
        st.caption("Sin fuentes recuperadas para esta respuesta.")
        return

    for indice, fuente in enumerate(fuentes, start=1):
        documento = fuente.get("documento") or "Documento"
        articulo = fuente.get("articulo") or "?"
        st.markdown(f"**{indice}. {documento} — Artículo {articulo}**")
        detalles = [
            fuente.get("titulo") or "",
            fuente.get("capitulo") or "",
            f"id: {fuente.get('id') or 'n/d'}",
            f"score: {_formatear_score(fuente.get('score'))}",
        ]
        st.caption(" · ".join(detalle for detalle in detalles if detalle))
        fragmento = fuente.get("fragmento") or ""
        if fragmento:
            cita = fragmento.replace("\n", "\n> ")
            st.markdown(f"> {cita}")
        if indice < len(fuentes):
            st.divider()


def _mostrar_meta(resultado: dict[str, Any] | None) -> None:
    if not resultado:
        st.caption("Aún no hay una respuesta para inspeccionar.")
        return

    en_alcance = resultado.get("en_alcance")
    if en_alcance is True:
        st.success("Dentro de alcance")
    elif en_alcance is False:
        st.warning("Fuera de alcance o sin sustento")

    motivo = resultado.get("motivo") or "n/d"
    modo = resultado.get("modo") or "n/d"
    modelo = resultado.get("modelo") or "n/d"
    latencia = resultado.get("latencia_s")
    latencia_texto = f"{float(latencia):.1f} s" if isinstance(latencia, (int, float)) else "n/d"

    st.write(f"Motivo: `{motivo}`")
    st.write(f"Modo: `{modo}`")
    st.write(f"Modelo: `{modelo}`")
    st.write(f"Latencia: `{latencia_texto}`")

    citas_invalidas = resultado.get("citas_invalidas") or []
    if citas_invalidas:
        st.error("Citas inválidas: " + ", ".join(str(c) for c in citas_invalidas))

    if resultado.get("requiere_revision"):
        st.warning("Esta respuesta requiere revisión humana.")
    if resultado.get("advertencia"):
        st.warning(resultado["advertencia"])


if "sesion_id" not in st.session_state:
    parametro = st.query_params.get("sesion")
    if isinstance(parametro, list):
        parametro = parametro[0] if parametro else None
    st.session_state.sesion_id = parametro or _nueva_sesion()
    st.query_params["sesion"] = st.session_state.sesion_id

if "mensajes" not in st.session_state:
    st.session_state.mensajes = _cargar_historial(st.session_state.sesion_id)

if "historial_cargado" not in st.session_state:
    st.session_state.historial_cargado = True
    ultimo = next(
        (
            mensaje["meta"]
            for mensaje in reversed(st.session_state.mensajes)
            if mensaje.get("role") == "assistant" and mensaje.get("meta")
        ),
        None,
    )
    st.session_state.ultimo_resultado = ultimo

if "ultimo_resultado" not in st.session_state:
    st.session_state.ultimo_resultado = None


with st.sidebar:
    st.header("Transparencia")
    salud = _salud()

    if "error" in salud:
        st.error("API no disponible")
        st.caption(f"Verifica que uvicorn esté corriendo en {API_URL}")
    else:
        if salud.get("status") == "ok":
            st.success("Sistema listo")
        else:
            st.warning("Sistema degradado")
        st.write(f"Modelo: `{salud.get('modelo', 'n/d')}`")
        st.write(f"Ollama: {'disponible' if salud.get('ollama') else 'no disponible'}")
        st.write(f"Índice: {'listo' if salud.get('db') else 'sin índice'}")
        st.caption(
            f"Colección: {salud.get('coleccion', 'n/d')} "
            f"({salud.get('chunks', 0)} artículos, "
            f"{salud.get('subchunks', 0)} subchunks)"
        )

    if st.button("Actualizar estado", use_container_width=True):
        _salud.clear()
        st.rerun()

    st.divider()
    st.caption(f"Sesión: `{st.session_state.sesion_id[:8]}`")

    if st.button("Nueva conversación", use_container_width=True):
        try:
            httpx.delete(
                f"{API_URL}/sesiones/{st.session_state.sesion_id}",
                timeout=TIMEOUT_CORTO,
            )
        except Exception:
            pass
        st.session_state.sesion_id = _nueva_sesion()
        st.query_params["sesion"] = st.session_state.sesion_id
        st.session_state.mensajes = []
        st.session_state.ultimo_resultado = None
        st.session_state.historial_cargado = True
        st.rerun()

    st.divider()
    st.subheader("Respuesta y verificación")
    _mostrar_meta(st.session_state.get("ultimo_resultado"))

    st.divider()
    st.subheader("Fuentes recuperadas")
    ultimo = st.session_state.get("ultimo_resultado") or {}
    _mostrar_fuentes(ultimo.get("fuentes") or [])


st.title("Mini-Juztina")
st.caption(
    "Asistente legal local sobre la Constitución Política del Perú y el Código "
    "Penal peruano. Herramienta informativa, no asesoría legal personalizada."
)

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje.get("role", "assistant")):
        st.markdown(mensaje.get("content", ""))
        meta = mensaje.get("meta")
        if meta:
            piezas = [
                f"Motivo: {meta.get('motivo') or 'n/d'}",
                f"Modo: {meta.get('modo') or 'n/d'}",
            ]
            if isinstance(meta.get("latencia_s"), (int, float)):
                piezas.append(f"Latencia: {float(meta['latencia_s']):.1f} s")
            st.caption(" · ".join(piezas))
            if meta.get("advertencia"):
                st.warning(meta["advertencia"])
            if meta.get("requiere_revision"):
                st.caption("Requiere revisión humana.")

consulta = st.chat_input("Escribe tu consulta sobre la Constitución o el Código Penal")

if consulta:
    consulta = consulta.strip()
    if consulta:
        st.session_state.mensajes.append({"role": "user", "content": consulta, "meta": None})
        with st.chat_message("user"):
            st.markdown(consulta)

        with st.spinner(
            "Buscando en las fuentes y consultando al modelo local. "
            "En CPU puede tardar decenas de segundos..."
        ):
            try:
                resultado = _enviar_consulta(consulta)
            except Exception as exc:
                detalle = str(exc)[:800]
                resultado = {
                    "pregunta": consulta,
                    "respuesta": f"No se pudo completar la consulta: {detalle}",
                    "fuentes": [],
                    "en_alcance": False,
                    "motivo": "error",
                    "modo": "api",
                    "advertencia": detalle,
                    "citas_detectadas": [],
                    "citas_invalidas": [],
                    "requiere_revision": True,
                    "modelo": "",
                    "k": 0,
                    "latencia_s": None,
                }

        st.session_state.mensajes.append(
            {
                "role": "assistant",
                "content": resultado.get("respuesta", ""),
                "meta": resultado,
            }
        )
        st.session_state.ultimo_resultado = resultado
        st.rerun()
