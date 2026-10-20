# Entregables oficiales — Mini-Juztina

Mapa entre los entregables exigidos, los artefactos del repositorio, el responsable y el criterio de aceptación.

## 1. Repositorio de código fuente

**Qué debe demostrar:** código estructurado, limpio y documentado, con buenas prácticas de arquitectura.

| Artefacto | Ubicación | Responsable |
|---|---|---|
| Código de ingesta, chunking, embeddings, retriever y RAG | `src/` | A |
| API FastAPI e historial | `src/api.py`, `src/db.py` | B |
| UI Streamlit + panel de transparencia | `app/` | B |
| Prompt y guardrails | `prompts/` | B (revisa A) |
| Pruebas y reportes | `tests/` | Ambos |
| Arquitectura y decisiones | `docs/ARQUITECTURA.md`, `DECISIONS.md` | Ambos |
| Instalación y estructura | `README.md`, `requirements.txt`, `.gitignore` | Ambos |

**Criterio de aceptación**

- [ ] Estructura de carpetas clara y coherente con `README.md`.
- [ ] Módulos con responsabilidad única y funciones documentadas.
- [ ] Sin credenciales, rutas absolutas ni secretos en el código.
- [ ] Dependencias fijadas en `requirements.txt`.
- [ ] `README.md` permite entender el proyecto en menos de 5 minutos.
- [ ] Historial de commits legible; ramas por rol integradas a `main`.
- [ ] Código corre localmente sin pasos ocultos.

---

## 2. Manual de instalación y despliegue local

**Qué debe demostrar:** una persona externa replica el entorno desde cero siguiendo el documento.

| Artefacto | Ubicación | Responsable |
|---|---|---|
| Manual paso a paso | `docs/MANUAL_INSTALACION.md` | B (A revisa la parte de datos/índice) |
| Comando único de arranque | `run.ps1` / `docker-compose.yml` | B |
| Registro de fuentes y fechas | `data/raw/FUENTES.md` | A |

**Criterio de aceptación**

- [ ] Cubre: requisitos, venv, dependencias, Ollama, descarga de modelo, fuentes, ingesta, chunking, embeddings, inicialización de ChromaDB, API y UI.
- [ ] Incluye comandos exactos y resultados esperados.
- [ ] Incluye verificación de la base vectorial y prueba offline.
- [ ] Incluye solución de problemas frecuentes.
- [ ] Otra persona (o el docente) lo ejecuta sin ayuda y llega a la UI funcional.
- [ ] El comando único levanta Ollama + API + UI.

---

## 3. Demostración en vivo (offline)

**Qué debe demostrar:** el prototipo funciona en tiempo real sin internet, con precisión, citas correctas y guardrails.

| Artefacto | Ubicación | Responsable |
|---|---|---|
| Guion y rúbrica de demo | `docs/DEMO.md` | Ambos |
| Slides | `docs/` o carpeta de presentación | Ambos |
| Evidencia de pruebas | `tests/report.md` | Ambos |
| Casos de demo verificados | `docs/DEMO.md` (sección 3) | A (citas) / B (operación) |

**Criterio de aceptación**

- [ ] Demo ejecutada con la red desconectada.
- [ ] Caso dentro de alcance con cita textual verificada contra el PDF oficial.
- [ ] Caso fuera de alcance: declina sin inventar.
- [ ] Caso sin sustento: responde "No encuentro sustento en las fuentes proporcionadas."
- [ ] Panel de transparencia visible con documento, artículo, fragmento y score.
- [ ] Duración ≤ 12 minutos y plan de respaldo listo.
- [ ] Métricas de precisión y latencia presentadas.

---

## 4. Mapa con el plan de trabajo

| Entregable | Pasos del plan | Semana |
|---|---|---|
| Repositorio de código fuente | 2, 6–7, 9–11, 14, 16–17, 18–20 | 1–3 |
| Manual de instalación y despliegue | 3, 23, 24 | 4 |
| Demo en vivo | 21–22, 25 | 4 |

## 5. Definición de "terminado" (global)

Un entregable está terminado cuando:

1. Existe en el repositorio y está enlazado desde `README.md`.
2. Otra persona del equipo puede ejecutarlo siguiendo la documentación.
3. Fue probado en local y, cuando corresponde, offline.
4. Está revisado por la persona que no lo escribió.
5. No expone datos sensibles ni depende de servicios en la nube.
