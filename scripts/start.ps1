param([switch]$Demo, [switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $dockerBin = Join-Path $env:ProgramFiles 'Docker/Docker/resources/bin'
        if (Test-Path (Join-Path $dockerBin 'docker.exe')) { $env:PATH = "$dockerBin;$env:PATH" }
    }
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Please start Docker Desktop first.' }
    docker compose up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Database/Redis startup failed.' }
    if (-not (Test-Path 'backend/.env')) { Copy-Item 'backend/.env.example' 'backend/.env' }
    if ($Demo) { $env:DEMO_MODE = 'true' }
    if (-not $SkipInstall) {
        if (-not (Test-Path 'backend/.venv/Scripts/python.exe')) {
            python -m venv backend/.venv
            if ($LASTEXITCODE -ne 0) { throw 'Python 3.12+ is required.' }
        }
        & './backend/.venv/Scripts/python.exe' -m pip install uv
        if ($LASTEXITCODE -ne 0) { throw 'Dependency tool installation failed.' }
        Push-Location backend
        try {
            & './.venv/Scripts/uv.exe' sync --frozen --inexact
            if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
        } finally { Pop-Location }
        Push-Location frontend
        try {
            npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
            npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        } finally { Pop-Location }
    }
    Push-Location backend
    try {
        & './.venv/Scripts/python.exe' -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    } finally { Pop-Location }
    & './backend/.venv/Scripts/python.exe' scripts/run_local.py
    if ($LASTEXITCODE -ne 0) { throw 'Local services stopped unexpectedly. Check backend/var/logs.' }
} finally { Pop-Location }
