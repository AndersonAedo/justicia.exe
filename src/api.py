"""API local de Mini-Juztina (FastAPI).

Capa B sobre el contrato de A: ``src.rag_pipeline.responder()`` devuelve la
respuesta, las fuentes y los metadatos de verificación. Esta API agrega el
historial por sesión y expone el contrato HTTP que consume Streamlit.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Callable

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from src import config, db

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=config.MAX_MENSAJE_CHARS)
    sesion_id: str = Field(default="default", min_length=1, max_length=128)

    @field_validator("mensaje", "sesion_id")
    @classmethod
    def _sin_espacios_extremos(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("no puede estar vacío")
        return valor


class Fuente(BaseModel):
    id: str = ""
    documento: str = ""
    titulo: str = ""
    capitulo: str = ""
    articulo: str = ""
    fragmento: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    pregunta: str
    respuesta: str
    fuentes: list[Fuente]
    en_alcance: bool
    motivo: str = ""
    modo: str = ""
    advertencia: str = ""
    citas_detectadas: list[str] = Field(default_factory=list)
    citas_invalidas: list[str] = Field(default_factory=list)
    requiere_revision: bool = False
    modelo: str = ""
    k: int = config.TOP_K
    latencia_s: float = 0.0


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    db: bool
    modelo: str
    coleccion: str
    subcoleccion: str
    chunks: int = 0
    subchunks: int = 0
    version: str = "0.1.0"


class Turno(BaseModel):
    id: int
    sesion_id: str
    rol: str
    contenido: str
    fuentes: list[Fuente]
    en_alcance: bool | None = None
    motivo: str = ""
    modo: str = ""
    advertencia: str = ""
    citas_invalidas: list[str] = Field(default_factory=list)
    requiere_revision: bool = False
    latencia_s: float | None = None
    modelo: str = ""
    creado_en: str


class HistorialResponse(BaseModel):
    sesion_id: str
    turnos: list[Turno]


def _ollama_available() -> bool:
    try:
        respuesta = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=2.0)
        return respuesta.status_code == 200
    except httpx.HTTPError:
        return False


def _db_status() -> tuple[bool, int, int]:
    """Devuelve (disponible, artículos, subchunks) sin importar Chroma al inicio."""
    try:
        import chromadb
    except Exception:
        return False, 0, 0
    try:
        cliente = chromadb.PersistentClient(path=str(config.DB_DIR))
        principal = cliente.get_collection(config.COLLECTION)
        chunks = int(principal.count())
        try:
            subcoleccion = cliente.get_collection(config.SUBCOLLECTION)
            subchunks = int(subcoleccion.count())
        except Exception:
            subchunks = 0
        return chunks > 0, chunks, subchunks
    except Exception:
        return False, 0, 0


def _responder() -> Callable[..., dict[str, Any]]:
    """Carga perezosa del pipeline de A (evita importar Chroma en /health)."""
    from src.rag_pipeline import responder

    return responder


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    logger.info("Historial SQLite inicializado en %s", config.HISTORY_DB)
    yield


app = FastAPI(
    title="Mini-Juztina API",
    description=(
        "Asistente legal local sobre la Constitución Política del Perú y el "
        "Código Penal peruano. No es asesoría legal personalizada."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def inicio() -> dict[str, str]:
    return {
        "nombre": "Mini-Juztina",
        "docs": "/docs",
        "chat": "/chat",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ollama_ok = _ollama_available()
    db_ok, chunks, subchunks = _db_status()
    return HealthResponse(
        status="ok" if ollama_ok and db_ok else "degraded",
        ollama=ollama_ok,
        db=db_ok,
        modelo=config.OLLAMA_MODEL,
        coleccion=config.COLLECTION,
        subcoleccion=config.SUBCOLLECTION,
        chunks=chunks,
        subchunks=subchunks,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    historial = db.obtener_historial_llm(
        payload.sesion_id,
        limite_pares=config.HISTORY_TURNS,
    )
    try:
        resultado = _responder()(
            payload.mensaje,
            k=config.TOP_K,
            historial=historial,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudo cargar el pipeline RAG. Verifica que chromadb y "
                "sentence-transformers estén instalados y que exista el índice."
            ),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - salvaguarda de la API
        logger.exception("Error inesperado en /chat")
        raise HTTPException(
            status_code=500,
            detail="Error interno al procesar la consulta.",
        ) from exc

    try:
        db.guardar_turno(payload.sesion_id, "user", payload.mensaje)
        db.guardar_turno(
            payload.sesion_id,
            "assistant",
            resultado["respuesta"],
            fuentes=resultado.get("fuentes") or [],
            en_alcance=resultado.get("en_alcance"),
            motivo=resultado.get("motivo", ""),
            modo=resultado.get("modo", ""),
            advertencia=resultado.get("advertencia", ""),
            citas_invalidas=resultado.get("citas_invalidas") or [],
            requiere_revision=bool(resultado.get("requiere_revision")),
            latencia_s=resultado.get("latencia_s"),
            modelo=resultado.get("modelo", ""),
        )
    except Exception:  # el chat no debe caerse por un fallo del historial
        logger.exception("No se pudo guardar el turno en SQLite")

    return ChatResponse(**resultado)


@app.get("/sesiones/{sesion_id}/historial", response_model=HistorialResponse)
def historial(
    sesion_id: str,
    limite: int = Query(default=50, ge=1, le=200),
) -> HistorialResponse:
    turnos = db.obtener_turnos(sesion_id, limite=limite)
    return HistorialResponse(sesion_id=sesion_id, turnos=turnos)


@app.delete("/sesiones/{sesion_id}")
def limpiar(sesion_id: str) -> dict[str, Any]:
    eliminados = db.limpiar_sesion(sesion_id)
    return {"sesion_id": sesion_id, "eliminados": eliminados}
