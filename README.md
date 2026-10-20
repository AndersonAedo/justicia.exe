# Mini-Juztina

Asistente legal 100% local (offline) especializado en la **Constitución Política del Perú** y el **Código Penal peruano**. Implementa un pipeline RAG (*Retrieval-Augmented Generation*) sobre ChromaDB y Ollama, con API FastAPI, base de datos SQLite para historial y frontend interactivo en Streamlit con panel de transparencia. **No requiere ni utiliza ningún servicio o API en la nube.**

---

## 🎯 Estado del Proyecto

- **Parte A (Datos + RAG):** Ingesta oficial SPIJ, chunking jerárquico (786 artículos canónicos), subchunking por incisos (1,314 subchunks), base vectorial ChromaDB, retriever híbrido (semántico + bonificación léxica) y pipeline RAG validado.
- **Parte B (Aplicación + UI + Pruebas):** Backend FastAPI (`src/api.py`), historial SQLite persistente (`src/db.py`), frontend Streamlit con panel de transparencia (`app/ui.py`), script de arranque integrado (`run.ps1`), pruebas unitarias (`tests/test_api.py`, `tests/test_db.py`), matriz de guardrails (`tests/test_guardrails.md`) y reporte de pruebas integrado (`tests/report.md`).

---

## 📦 Entregables del Proyecto

| Entregable | Ubicación / Artefacto |
|---|---|
| **Código Fuente Completo** | `src/` (backend y RAG), `app/` (UI Streamlit), `tests/`, `prompts/` |
| **Manual de Instalación y Despliegue** | [`docs/MANUAL_INSTALACION.md`](docs/MANUAL_INSTALACION.md) |
| **Documento de Arquitectura** | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |
| **Registro de Decisiones Técnicas** | [`DECISIONS.md`](DECISIONS.md) |
| **Guion de Demostración en Vivo** | [`docs/DEMO.md`](docs/DEMO.md) |
| **Reporte Integral de Pruebas** | [`tests/report.md`](tests/report.md) |

---

## 📁 Estructura del Repositorio

```
justicia.exe/
├── data/
│   ├── raw/             # PDFs oficiales del SPIJ (Constitución y Código Penal)
│   ├── clean/           # Texto depurado sin encabezados ni notas al pie
│   ├── chunks/          # Chunks canónicos en JSONL (1 artículo por chunk)
│   └── subchunks/       # Subchunks por incisos para máxima precisión de búsqueda
├── db/                  # Índice ChromaDB y base de datos SQLite de historial
├── src/
│   ├── api.py           # API REST FastAPI con Swagger (/docs), /chat y /health
│   ├── db.py            # Gestión del historial SQLite por sesión
│   ├── config.py        # Configuración centralizada de rutas y parámetros
│   ├── ingest.py        # Extracción y limpieza desde PDFs oficiales
│   ├── chunker.py       # Segmentación canónica de artículos legales
│   ├── build_subchunks.py # Segmentación de incisos y artículos extensos
│   ├── embedder.py      # Generación de embeddings con multilingual-e5-base
│   ├── retriever.py     # Motor de búsqueda híbrido (semántico + léxico)
│   └── rag_pipeline.py  # Pipeline RAG con control de citas y guardrails
├── app/
│   └── ui.py            # Interfaz Streamlit con chat y panel de transparencia
├── prompts/
│   └── system_prompt.txt # System prompt legal con citas estrictas [S1], [S2]
├── tests/
│   ├── test_api.py      # Pruebas unitarias de FastAPI
│   ├── test_db.py       # Pruebas de persistencia y orden en SQLite
│   ├── test_guardrails.md # Matriz de casos de prueba y evaluación de límites
│   └── report.md        # Reporte consolidado de pruebas y latencias
├── docs/                # Documentación técnica y manuales
├── requirements.txt     # Dependencias del entorno Python
├── run.ps1              # Script PowerShell para iniciar Ollama + API + UI
├── DECISIONS.md         # Registro formal de decisiones de diseño
└── README.md
```

---

## ⚙️ Requisitos del Sistema

- **Sistema Operativo:** Windows 10/11, Linux o macOS.
- **Python:** 3.10 o 3.11.
- **Ollama:** Instalado localmente con el modelo `qwen2.5:3b` descargado.
- **Hardware:** Mínimo 8 GB de RAM (16 GB recomendados); 15 GB de disco libre. Compatible con CPU pura o aceleración GPU (NVIDIA CUDA).

---

## 🚀 Puesta en Marcha Rápida (Windows PowerShell)

### 1. Preparar Entorno Virtual e Instalar Dependencias
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Generar el Índice Vectorial Local (ChromaDB)
```powershell
python -m src.embedder --chunks data/chunks --collection legislacion_pe
python -m src.embedder --chunks data/subchunks --collection legislacion_pe_sub
```

### 3. Descargar y Levantar el Modelo en Ollama
```powershell
ollama pull qwen2.5:3b
ollama serve
```

### 4. Iniciar la Aplicación Completa con un Solo Comando
```powershell
.\run.ps1
```
El script `run.ps1` valida la disponibilidad de Ollama, arranca el backend FastAPI en `http://127.0.0.1:8000`, lanza la interfaz Streamlit en `http://127.0.0.1:8501` y abre el navegador automáticamente.

---

## 🧪 Ejecución de Pruebas Automatizadas

Para validar todos los componentes de la aplicación de manera local:

```powershell
# Ejecutar todas las pruebas unitarias (API y Base de datos SQLite)
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🛡️ Principios Arquitectónicos y Guardrails

1. **100% On-Premise y Offline:** Garantía de privacidad absoluta; ningún dato, consulta o fragmento legal viaja a servidores externos.
2. **Citas Obligatorias y Verificables:** Toda afirmación normativa cita documento, artículo y fragmento textual real.
3. **Control de Alucinaciones:** Algoritmo de postproceso que verifica que ningún artículo mencionado en la respuesta sea inventado.
4. **Guardrail de Alcance Temático:** Filtro determinista que declina de forma inmediata consultas laborales, civiles o tributarias.
5. **Panel de Transparencia:** Permite al usuario auditar en tiempo real qué artículos y puntuaciones sustentan la respuesta entregada.
