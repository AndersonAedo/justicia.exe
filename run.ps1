param(
    [switch]$NoBrowser,
    [int]$ApiPort = 8000,
    [int]$UiPort = 8501
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

if (-not $env:MJ_OLLAMA_MODEL) {
    $env:MJ_OLLAMA_MODEL = "qwen2.5:3b"
}
$modelo = $env:MJ_OLLAMA_MODEL

function Test-Url {
    param([string]$Url)
    try {
        $respuesta = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 -ErrorAction Stop
        return ($respuesta.StatusCode -ge 200 -and $respuesta.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Wait-Url {
    param([string]$Url, [int]$Seconds = 60)
    $limite = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $limite) {
        if (Test-Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host "Mini-Juztina: iniciando servicios..."
Write-Host "Raiz: $root"
Write-Host "Modelo: $modelo"

# Detectar Ollama en PATH o en carpeta por defecto
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    $defaultOllama = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
    if (Test-Path (Join-Path $defaultOllama "ollama.exe")) {
        $env:Path = "$defaultOllama;$env:Path"
    }
}

if (-not (Test-Url "http://127.0.0.1:11434/api/tags")) {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Write-Error "Ollama no esta instalado o no esta en PATH. Instalalo desde https://ollama.com/download"
        exit 1
    }
    Write-Host "Iniciando Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized | Out-Null
    if (-not (Wait-Url "http://127.0.0.1:11434/api/tags" 45)) {
        Write-Error "Ollama no respondio en 45 s. Ejecuta 'ollama serve' manualmente."
        exit 1
    }
}
Write-Host "Ollama: OK"

try {
    $tags = ollama list 2>$null
    if ($tags -notmatch [regex]::Escape($modelo)) {
        Write-Host "Descargando modelo local '$modelo' en Ollama..."
        ollama pull $modelo
    }
} catch {
}

$dbDir = if ($env:MJ_DB_DIR) { $env:MJ_DB_DIR } else { Join-Path $root "db" }
$dbOk = $false
if (Test-Path -LiteralPath $dbDir) {
    $dbOk = [bool](Get-ChildItem -LiteralPath $dbDir -Filter "*.sqlite3" -ErrorAction SilentlyContinue)
}
if (-not $dbOk) {
    Write-Warning "No se detecta el indice Chroma en '$dbDir'. Ejecuta los dos comandos de src.embedder del manual."
}

if (-not (Test-Url "http://127.0.0.1:$ApiPort/health")) {
    Write-Host "Iniciando API en http://127.0.0.1:$ApiPort ..."
    Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", "$ApiPort") -WorkingDirectory $root -WindowStyle Normal | Out-Null
    if (-not (Wait-Url "http://127.0.0.1:$ApiPort/health" 45)) {
        Write-Error "La API no respondio en 45 s. Revisa la ventana de uvicorn."
        exit 1
    }
}
Write-Host "API: OK"

$env:MJ_API_URL = "http://127.0.0.1:$ApiPort"

if (-not (Test-Url "http://127.0.0.1:$UiPort")) {
    Write-Host "Iniciando UI en http://127.0.0.1:$UiPort ..."
    Start-Process -FilePath $python -ArgumentList @("-m", "streamlit", "run", "app/ui.py", "--server.port", "$UiPort", "--server.headless", "true") -WorkingDirectory $root -WindowStyle Normal | Out-Null
    if (-not (Wait-Url "http://127.0.0.1:$UiPort" 45)) {
        Write-Error "La UI no respondio en 45 s. Revisa la ventana de streamlit."
        exit 1
    }
}
Write-Host "UI: OK"

$url = "http://127.0.0.1:$UiPort"
if (-not $NoBrowser) {
    Start-Process $url | Out-Null
}
Write-Host "Mini-Juztina listo en $url"
