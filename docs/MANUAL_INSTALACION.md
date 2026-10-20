# Manual de instalación y despliegue local — Mini-Juztina

Guía paso a paso para replicar el entorno **desde cero** en Windows (PowerShell). Incluye equivalencias para Linux/macOS. Al finalizar tendrás Ollama, el índice vectorial, la API y la UI corriendo **sin conexión a internet**.

> Tiempo estimado: 30–45 min (sin contar la descarga de modelos y PDFs).
> Este manual se actualiza a medida que se implementan los módulos. Los comandos marcados con `(contrato)` definen la interfaz CLI acordada entre A y B.

---

## 0. Requisitos

### Hardware

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 8 GB (modelo 3B) | 16 GB (modelo 7B/8B) |
| Disco libre | 10 GB | 20–25 GB |
| GPU | No obligatoria | NVIDIA con ≥8 GB VRAM (opcional) |
| CPU | 4 núcleos | 8 núcleos |

### Software

- Windows 10/11 (o Linux/macOS)
- Python **3.10+** (`python --version`)
- Git (opcional si se copia la carpeta)
- [Ollama](https://ollama.com/download) para Windows
- Navegador actualizado (Chrome/Edge/Firefox)

### Internet

Solo se necesita para la instalación inicial: descargar dependencias, el modelo de Ollama y los PDFs oficiales. Después de eso, todo funciona offline.

---

## 1. Obtener el proyecto

```powershell
cd $HOME\Desktop
git clone <URL_DEL_REPO> mini-juztina
cd mini-juztina
```

Si todavía no hay repositorio remoto, copia la carpeta `mini-juztina` completa y entra en ella.

Verifica la estructura:

```powershell
Get-ChildItem
```

Debes ver `src/`, `app/`, `data/`, `db/`, `docs/`, `tests/`, `requirements.txt` y `README.md`.

---

## 2. Crear y activar el entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Debe aparecer `(.venv)` al inicio del prompt. Actualiza pip:

```powershell
python -m pip install --upgrade pip
```

---

## 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

Verificación rápida:

```powershell
python -c "import fastapi, streamlit, chromadb, sentence_transformers, pdfplumber; print('OK')"
```

> **GPU opcional (NVIDIA):** si `sentence-transformers` no detecta la GPU, instala la versión CUDA de PyTorch según https://pytorch.org/get-started/locally/ y vuelve a probar. Si no hay GPU, todo funciona en CPU (más lento).

---

## 4. Instalar y verificar Ollama

1. Instala Ollama desde https://ollama.com/download.
2. Abre una **terminal nueva** y comprueba:

```powershell
ollama --version
ollama list
```

3. Descarga el modelo elegido (ver `DECISIONS.md`). Opciones:

```powershell
# Recomendado para CPU y demo
ollama pull qwen2.5:3b

# Opcional si hay RAM/GPU
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

4. Inicia el servidor local (si no está corriendo como servicio):

```powershell
ollama serve
```

5. Prueba una respuesta:

```powershell
ollama run qwen2.5:3b "Responde solo: listo"
```

6. Verifica la API local:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

**Debe devolver la lista de modelos.** Si falla, revisa la sección de solución de problemas.

---

## 5. Descargar las fuentes legales

1. Descarga la **Constitución Política del Perú** y el **Código Penal** vigentes desde SPIJ, Congreso o TC.
2. Guárdalos en `data/raw/` con nombres claros, por ejemplo:
   - `data/raw/constitucion_2026.pdf`
   - `data/raw/codigo_penal_2026.pdf`
3. Registra URL, fecha y nombre en `data/raw/FUENTES.md`.
4. Comprueba que los PDFs tengan texto seleccionable (abre uno y arrastra el cursor). Si son escaneados, aplica OCR y déjalo documentado.

---

## 6. Construir el corpus y el índice vectorial

Ejecuta los pasos **en orden**. Todos usan rutas relativas a la raíz del proyecto y el entorno `.venv` activado.

### 6.1 Limpieza de PDFs a texto

```powershell
python -m src.ingest --input data/raw --output data/clean
```

Resultado esperado: `data/clean/constitucion.txt` y `data/clean/codigo_penal.txt`.

### 6.2 Chunking por artículo

```powershell
python -m src.chunker --input data/clean --output data/chunks
```

Resultado esperado: `data/chunks/constitucion.jsonl` y `data/chunks/codigo_penal.jsonl`, un artículo por línea.

Verificación rápida:

```powershell
python -c "import json; l=[json.loads(x) for x in open('data/chunks/codigo_penal.jsonl',encoding='utf-8')]; print(len(l), l[0]['id'], l[0]['articulo'])"
```

### 6.3 Subchunks por inciso

Los artículos largos (por ejemplo, el artículo 2 de la Constitución) diluyen su embedding. Este paso genera fragmentos de 300–700 caracteres con el encabezado del artículo repetido y guarda `parent_id`:

```powershell
python -m src.build_subchunks
```

Resultado esperado: `data/subchunks/*.jsonl` (~1 300 subchunks).

### 6.4 Embeddings y base vectorial

```powershell
python -m src.embedder --chunks data/chunks --persist db --collection legislacion_pe
python -m src.embedder --chunks data/subchunks --persist db --collection legislacion_pe_sub
```

La primera ejecución descarga el modelo `intfloat/multilingual-e5-base` (requiere internet). Las siguientes funcionan offline.

Resultado esperado: carpeta `db/` con las colecciones `legislacion_pe` (786 chunks) y `legislacion_pe_sub` (~1 314 subchunks).

### 6.5 Probar el pipeline RAG

```powershell
python -m src.rag_pipeline "¿Qué protege la libertad de expresión?" --k 5 --json
python -m src.rag_pipeline "¿Cuánto me corresponde de CTS este año?" --json
```

La primera consulta debe citar la Constitución, artículo 2; la segunda debe
declinar por estar fuera de alcance. En CPU la primera puede tardar decenas de
segundos.

### 6.6 Verificar que el índice sobrevive al reinicio

Cierra la terminal, ábrela de nuevo, activa el venv y ejecuta:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import chromadb; c=chromadb.PersistentClient(path='db'); print('principal:', c.get_collection('legislacion_pe').count()); print('subchunks:', c.get_collection('legislacion_pe_sub').count())"
```

Ambos números deben ser mayores que 0.

> **Reconstruir el índice:** borra `db/` (o cambia de colección) y repite los pasos 6.4. No borres `data/chunks/` ni `data/subchunks/` salvo que quieras regenerarlos.

---

## 7. Ejecutar la API

En una terminal con el venv activo:

```powershell
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Verifica:

- Swagger: http://localhost:8000/docs
- Salud: http://localhost:8000/health

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Debe devolver un JSON con `status: "ok"`, `ollama: true` y `db: true`.

Prueba una consulta:

```powershell
$body = @{ mensaje = "¿Qué protege la libertad de expresión?"; sesion_id = "demo" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType "application/json" -Body $body
```

---

## 8. Ejecutar la interfaz

En **otra** terminal, con el venv activo (la API debe seguir corriendo):

```powershell
streamlit run app/ui.py --server.port 8501
```

Abre http://localhost:8501. Prueba una consulta dentro de alcance y revisa el panel de transparencia.

---

## 9. Despliegue en un comando

Cuando el Paso 23 esté implementado, el arranque completo será:

```powershell
.\run.ps1
```

o, con Docker:

```powershell
docker compose up --build
```

Debe levantar Ollama, la API y la UI. Comprueba los tres servicios antes de la demo.

---

## 10. Prueba offline real

1. Ejecuta al menos una consulta con internet conectado.
2. **Desconecta el Wi-Fi / cable de red** (o activa modo avión).
3. Reinicia Ollama, la API y la UI.
4. Repite una consulta dentro de alcance y una fuera de alcance.
5. Confirma con `Invoke-RestMethod http://localhost:8000/health` que todo sigue `ok`.

Criterio de aceptación: el sistema responde, cita y aplica guardrails sin red.

---

## 11. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ollama: command not found` | Ollama no está en PATH | Reinstala Ollama y abre una terminal nueva. |
| `Connection refused` a `:11434` | Servidor Ollama apagado | Ejecuta `ollama serve` o abre la app de Ollama. |
| `model not found` | Modelo no descargado | `ollama pull <modelo>` y revisa `ollama list`. |
| `No module named ...` | Venv no activado | Activa `.venv` y repite `pip install -r requirements.txt`. |
| `chromadb` bloqueado / error de índice | Otra instancia usa `db/` | Cierra API/UI y vuelve a abrir; si persiste, reconstruye el índice. |
| `collections` vacío | Embeddings no ejecutados | Repite el paso 6.3 y verifica `col.count()`. |
| Respuestas muy lentas | Modelo grande o poca RAM | Usa `qwen2.5:3b`; reduce `k` y `num_ctx`. |
| UI no conecta con la API | API apagada o puerto distinto | Verifica `http://localhost:8000/health` y la URL configurada en la UI. |
| `port already in use` | Otro proceso en 8000/8501 | Cambia el puerto (`--port 8001`) o cierra el proceso. |
| PDF sin texto | Documento escaneado | Aplica OCR y documenta el procedimiento en `data/raw/FUENTES.md`. |
| PowerShell bloquea scripts | Política de ejecución | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. |

---

## 12. Checklist de instalación

- [ ] Python 3.10+ y venv activo
- [ ] `pip install -r requirements.txt` sin errores
- [ ] `ollama list` muestra el modelo elegido
- [ ] PDFs en `data/raw/` y registrados en `FUENTES.md`
- [ ] `data/clean/*.txt` generados
- [ ] `data/chunks/*.jsonl` generados y validados
- [ ] `data/subchunks/*.jsonl` generados
- [ ] `db/` con colecciones `legislacion_pe` y `legislacion_pe_sub`, ambas con `count() > 0`
- [ ] `GET /health` devuelve `ok`
- [ ] UI responde en http://localhost:8501
- [ ] Panel de transparencia muestra documento, artículo, fragmento y score
- [ ] Prueba offline completada
