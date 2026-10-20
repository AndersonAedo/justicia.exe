"""Pruebas del historial SQLite para Mini-Juztina (rol B).

Verifica la persistencia de turnos, aislamiento por sesión, límites de
recuperación y el formato de pares usuario/asistente para el pipeline RAG.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src import db


class HistorialTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "historial.sqlite3"
        db.init_db(self.db_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_guardar_y_recuperar_en_orden(self) -> None:
        db.guardar_turno("s1", "user", "¿Qué protege la libertad de expresión?", db_path=self.db_path)
        db.guardar_turno(
            "s1",
            "assistant",
            "La Constitución garantiza la libertad de expresión.",
            fuentes=[
                {
                    "id": "CONST-Art-2",
                    "documento": "Constitución Política del Perú",
                    "titulo": "Título I",
                    "capitulo": "Capítulo I",
                    "articulo": "2",
                    "fragmento": "Toda persona tiene derecho...",
                    "score": 0.95,
                }
            ],
            en_alcance=True,
            motivo="",
            modo="llm",
            advertencia="",
            citas_invalidas=[],
            requiere_revision=False,
            latencia_s=1.2,
            modelo="qwen2.5:3b",
            db_path=self.db_path,
        )

        turnos = db.obtener_turnos("s1", db_path=self.db_path)

        self.assertEqual(len(turnos), 2)
        self.assertEqual([t["rol"] for t in turnos], ["user", "assistant"])
        self.assertEqual(turnos[1]["fuentes"][0]["id"], "CONST-Art-2")
        self.assertIs(turnos[1]["en_alcance"], True)
        self.assertEqual(turnos[1]["modo"], "llm")
        self.assertEqual(turnos[1]["modelo"], "qwen2.5:3b")

    def test_limite_devuelve_ultimos_turnos(self) -> None:
        for indice in range(6):
            db.guardar_turno("s2", "user", f"mensaje_{indice}", db_path=self.db_path)

        turnos = db.obtener_turnos("s2", limite=3, db_path=self.db_path)

        self.assertEqual(len(turnos), 3)
        self.assertEqual([t["contenido"] for t in turnos], ["mensaje_3", "mensaje_4", "mensaje_5"])

    def test_sesiones_aisladas(self) -> None:
        db.guardar_turno("sesion_a", "user", "Pregunta en A", db_path=self.db_path)
        db.guardar_turno("sesion_b", "user", "Pregunta en B", db_path=self.db_path)

        turnos_a = db.obtener_turnos("sesion_a", db_path=self.db_path)
        turnos_b = db.obtener_turnos("sesion_b", db_path=self.db_path)

        self.assertEqual(len(turnos_a), 1)
        self.assertEqual(len(turnos_b), 1)
        self.assertEqual(turnos_a[0]["contenido"], "Pregunta en A")
        self.assertEqual(turnos_b[0]["contenido"], "Pregunta en B")

    def test_limpiar_sesion(self) -> None:
        db.guardar_turno("s3", "user", "hola", db_path=self.db_path)
        db.guardar_turno("s3", "assistant", "hola respuesta", db_path=self.db_path)

        eliminados = db.limpiar_sesion("s3", db_path=self.db_path)

        self.assertEqual(eliminados, 2)
        self.assertEqual(db.obtener_turnos("s3", db_path=self.db_path), [])

    def test_rechaza_rol_invalido(self) -> None:
        with self.assertRaises(ValueError):
            db.guardar_turno("s4", "system", "no permitido", db_path=self.db_path)

    def test_obtener_historial_llm_formato_pares(self) -> None:
        db.guardar_turno("s5", "user", "pregunta 1", db_path=self.db_path)
        db.guardar_turno("s5", "assistant", "respuesta 1", db_path=self.db_path)
        db.guardar_turno("s5", "user", "pregunta 2", db_path=self.db_path)
        db.guardar_turno("s5", "assistant", "respuesta 2", db_path=self.db_path)

        pares = db.obtener_historial_llm("s5", limite_pares=2, db_path=self.db_path)

        self.assertEqual(len(pares), 2)
        self.assertEqual(
            pares,
            [
                {"usuario": "pregunta 1", "asistente": "respuesta 1"},
                {"usuario": "pregunta 2", "asistente": "respuesta 2"},
            ],
        )

    def test_obtener_historial_llm_turno_incompleto(self) -> None:
        db.guardar_turno("s6", "user", "pregunta sin respuesta", db_path=self.db_path)

        pares = db.obtener_historial_llm("s6", limite_pares=1, db_path=self.db_path)

        self.assertEqual(len(pares), 1)
        self.assertEqual(pares[0], {"usuario": "pregunta sin respuesta", "asistente": ""})


if __name__ == "__main__":
    unittest.main()
