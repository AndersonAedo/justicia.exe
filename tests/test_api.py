"""Pruebas de la API FastAPI para Mini-Juztina (rol B).

Verifica los endpoints /health, /chat, historial, control de errores y guardrails
usando TestClient con componentes de recuperación simulados.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import api, db


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "historial.sqlite3"
        self._db_patch = patch.object(db, "HISTORY_DB", self.db_path)
        self._db_patch.start()
        db.init_db(self.db_path)
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._db_patch.stop()
        self._tmp.cleanup()

    def test_inicio(self) -> None:
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)
        data = respuesta.json()
        self.assertEqual(data["nombre"], "Mini-Juztina")
        self.assertIn("/docs", data["docs"])

    def test_health_ok(self) -> None:
        with patch.object(api, "_ollama_available", return_value=True):
            with patch.object(api, "_db_status", return_value=(True, 786, 1314)):
                respuesta = self.client.get("/health")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["status"], "ok")
        self.assertIs(cuerpo["ollama"], True)
        self.assertIs(cuerpo["db"], True)
        self.assertEqual(cuerpo["chunks"], 786)
        self.assertEqual(cuerpo["subchunks"], 1314)

    def test_health_degradado_sin_indice(self) -> None:
        with patch.object(api, "_ollama_available", return_value=True):
            with patch.object(api, "_db_status", return_value=(False, 0, 0)):
                respuesta = self.client.get("/health")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["status"], "degraded")
        self.assertIs(cuerpo["ollama"], True)
        self.assertIs(cuerpo["db"], False)

    def test_chat_dentro_de_alcance_y_guarda_historial(self) -> None:
        mock_resultado = {
            "pregunta": "¿Qué protege la libertad de expresión?",
            "respuesta": "La Constitución protege la libertad de información y expresión en su artículo 2.",
            "fuentes": [
                {
                    "id": "CONST-Art-2",
                    "documento": "Constitución Política del Perú",
                    "titulo": "Título I",
                    "capitulo": "Capítulo I",
                    "articulo": "2",
                    "fragmento": "Toda persona tiene derecho a las libertades de información...",
                    "score": 0.92,
                }
            ],
            "en_alcance": True,
            "motivo": "",
            "modo": "llm",
            "advertencia": "",
            "citas_detectadas": ["CONST-Art-2"],
            "citas_invalidas": [],
            "requiere_revision": False,
            "modelo": "qwen2.5:3b",
            "k": 5,
            "latencia_s": 1.5,
        }

        with patch.object(api, "_responder", return_value=lambda *a, **kw: mock_resultado):
            respuesta = self.client.post(
                "/chat",
                json={"mensaje": "¿Qué protege la libertad de expresión?", "sesion_id": "s_chat_1"},
            )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos["en_alcance"])
        self.assertEqual(len(datos["fuentes"]), 1)
        self.assertEqual(datos["fuentes"][0]["id"], "CONST-Art-2")

        historial = self.client.get("/sesiones/s_chat_1/historial")
        self.assertEqual(historial.status_code, 200)
        turnos = historial.json()["turnos"]
        self.assertEqual(len(turnos), 2)
        self.assertEqual(turnos[0]["rol"], "user")
        self.assertEqual(turnos[1]["rol"], "assistant")
        self.assertEqual(turnos[1]["fuentes"][0]["id"], "CONST-Art-2")

    def test_chat_fuera_de_alcance(self) -> None:
        mock_resultado = {
            "pregunta": "¿Cuánto me corresponde de CTS este año?",
            "respuesta": "Solo puedo responder consultas sobre la Constitución Política y el Código Penal.",
            "fuentes": [],
            "en_alcance": False,
            "motivo": "fuera_de_alcance",
            "modo": "guardrail",
            "advertencia": "",
            "citas_detectadas": [],
            "citas_invalidas": [],
            "requiere_revision": False,
            "modelo": "guardrail",
            "k": 5,
            "latencia_s": 0.01,
        }

        with patch.object(api, "_responder", return_value=lambda *a, **kw: mock_resultado):
            respuesta = self.client.post(
                "/chat",
                json={"mensaje": "¿Cuánto me corresponde de CTS este año?", "sesion_id": "s_chat_2"},
            )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertFalse(datos["en_alcance"])
        self.assertEqual(datos["motivo"], "fuera_de_alcance")
        self.assertEqual(datos["fuentes"], [])

    def test_mensaje_vacio_es_rechazado(self) -> None:
        respuesta = self.client.post(
            "/chat",
            json={"mensaje": "   ", "sesion_id": "s_vacio"},
        )
        self.assertEqual(respuesta.status_code, 422)

    def test_error_importacion_retorna_503(self) -> None:
        def fallo(*a, **kw):
            raise ImportError("chromadb missing")

        with patch.object(api, "_responder", return_value=fallo):
            respuesta = self.client.post(
                "/chat",
                json={"mensaje": "¿Cuál es la pena por hurto?", "sesion_id": "s_err1"},
            )

        self.assertEqual(respuesta.status_code, 503)
        self.assertIn("chromadb", respuesta.json()["detail"].lower())

    def test_error_tiempo_ejecucion_retorna_503(self) -> None:
        def fallo(*a, **kw):
            raise RuntimeError("Ollama no responde")

        with patch.object(api, "_responder", return_value=fallo):
            respuesta = self.client.post(
                "/chat",
                json={"mensaje": "¿Cuál es la pena por hurto?", "sesion_id": "s_err2"},
            )

        self.assertEqual(respuesta.status_code, 503)
        self.assertIn("ollama", respuesta.json()["detail"].lower())

    def test_limpiar_sesion(self) -> None:
        db.guardar_turno("s_delete", "user", "hola", db_path=self.db_path)
        db.guardar_turno("s_delete", "assistant", "hola!", db_path=self.db_path)

        borrado = self.client.delete("/sesiones/s_delete")
        self.assertEqual(borrado.status_code, 200)
        self.assertEqual(borrado.json()["eliminados"], 2)

        verificacion = self.client.get("/sesiones/s_delete/historial")
        self.assertEqual(verificacion.json()["turnos"], [])


if __name__ == "__main__":
    unittest.main()
