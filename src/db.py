"""Historial de conversación persistido en SQLite (rol B).

Guarda cada turno con la respuesta y los metadatos que devuelve el pipeline
RAG de A. Además expone ``obtener_historial_llm()`` con el formato que espera
``src.rag_pipeline.construir_mensajes()``: una lista de pares
``{"usuario": ..., "asistente": ...}``.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import HISTORY_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('user', 'assistant')),
    contenido TEXT NOT NULL,
    fuentes TEXT,
    en_alcance INTEGER,
    motivo TEXT,
    modo TEXT,
    advertencia TEXT,
    citas_invalidas TEXT,
    requiere_revision INTEGER,
    latencia_s REAL,
    modelo TEXT,
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turnos_sesion ON turnos (sesion_id, id);
"""

_COLUMNAS_NUEVAS = {
    "fuentes": "TEXT",
    "en_alcance": "INTEGER",
    "motivo": "TEXT",
    "modo": "TEXT",
    "advertencia": "TEXT",
    "citas_invalidas": "TEXT",
    "requiere_revision": "INTEGER",
    "latencia_s": "REAL",
    "modelo": "TEXT",
}


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else HISTORY_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrar(conn: sqlite3.Connection) -> None:
    existentes = {fila["name"] for fila in conn.execute("PRAGMA table_info(turnos)")}
    for columna, tipo in _COLUMNAS_NUEVAS.items():
        if columna not in existentes:
            conn.execute(f"ALTER TABLE turnos ADD COLUMN {columna} {tipo}")


def init_db(db_path: Path | None = None) -> None:
    """Crea la base y la tabla de turnos si no existen."""
    with closing(_connect(db_path)) as conn:
        conn.executescript(_SCHEMA)
        _migrar(conn)
        conn.commit()


def _json_o_none(valor: Any) -> str | None:
    if valor in (None, [], {}):
        return None
    return json.dumps(valor, ensure_ascii=False)


def guardar_turno(
    sesion_id: str,
    rol: str,
    contenido: str,
    *,
    fuentes: list[dict[str, Any]] | None = None,
    en_alcance: bool | None = None,
    motivo: str = "",
    modo: str = "",
    advertencia: str = "",
    citas_invalidas: list[str] | None = None,
    requiere_revision: bool = False,
    latencia_s: float | None = None,
    modelo: str = "",
    db_path: Path | None = None,
) -> int:
    """Guarda un turno y devuelve su id."""
    if rol not in {"user", "assistant"}:
        raise ValueError("rol debe ser 'user' o 'assistant'")
    if not sesion_id.strip():
        raise ValueError("sesion_id no puede estar vacío")
    if not contenido.strip():
        raise ValueError("contenido no puede estar vacío")

    creado = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect(db_path)) as conn:
        cursor = conn.execute(
            """
            INSERT INTO turnos (
                sesion_id, rol, contenido, fuentes, en_alcance, motivo, modo,
                advertencia, citas_invalidas, requiere_revision, latencia_s,
                modelo, creado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sesion_id,
                rol,
                contenido,
                _json_o_none(fuentes),
                None if en_alcance is None else int(en_alcance),
                motivo or None,
                modo or None,
                advertencia or None,
                _json_o_none(citas_invalidas),
                int(bool(requiere_revision)),
                latencia_s,
                modelo or None,
                creado,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _turno_desde_fila(fila: sqlite3.Row) -> dict[str, Any]:
    fuentes = json.loads(fila["fuentes"]) if fila["fuentes"] else []
    citas_invalidas = json.loads(fila["citas_invalidas"]) if fila["citas_invalidas"] else []
    return {
        "id": fila["id"],
        "sesion_id": fila["sesion_id"],
        "rol": fila["rol"],
        "contenido": fila["contenido"],
        "fuentes": fuentes,
        "en_alcance": None if fila["en_alcance"] is None else bool(fila["en_alcance"]),
        "motivo": fila["motivo"] or "",
        "modo": fila["modo"] or "",
        "advertencia": fila["advertencia"] or "",
        "citas_invalidas": citas_invalidas,
        "requiere_revision": bool(fila["requiere_revision"]),
        "latencia_s": fila["latencia_s"],
        "modelo": fila["modelo"] or "",
        "creado_en": fila["creado_en"],
    }


def obtener_turnos(
    sesion_id: str,
    limite: int | None = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Devuelve los últimos ``limite`` turnos en orden cronológico."""
    if limite is not None and limite <= 0:
        return []

    consulta = "SELECT * FROM turnos WHERE sesion_id = ?"
    parametros: list[Any] = [sesion_id]
    if limite is not None:
        consulta = (
            "SELECT * FROM ("
            + consulta
            + " ORDER BY id DESC LIMIT ?) ORDER BY id ASC"
        )
        parametros.append(limite)
    else:
        consulta += " ORDER BY id ASC"

    with closing(_connect(db_path)) as conn:
        filas = conn.execute(consulta, parametros).fetchall()
    return [_turno_desde_fila(fila) for fila in filas]


def obtener_historial_llm(
    sesion_id: str,
    limite_pares: int = 3,
    db_path: Path | None = None,
) -> list[dict[str, str]]:
    """Devuelve los últimos pares usuario/asistente para el pipeline de A."""
    if limite_pares <= 0:
        return []
    turnos = obtener_turnos(sesion_id, limite=limite_pares * 2, db_path=db_path)

    pares: list[dict[str, str]] = []
    usuario: str | None = None
    for turno in turnos:
        if turno["rol"] == "user":
            if usuario is not None:
                pares.append({"usuario": usuario, "asistente": ""})
            usuario = turno["contenido"]
        elif usuario is not None:
            pares.append({"usuario": usuario, "asistente": turno["contenido"]})
            usuario = None

    if usuario is not None:
        pares.append({"usuario": usuario, "asistente": ""})
    return pares[-limite_pares:]


def limpiar_sesion(sesion_id: str, db_path: Path | None = None) -> int:
    """Elimina todos los turnos de una sesión y devuelve cuántos borró."""
    with closing(_connect(db_path)) as conn:
        cursor = conn.execute("DELETE FROM turnos WHERE sesion_id = ?", (sesion_id,))
        conn.commit()
        return int(cursor.rowcount)
