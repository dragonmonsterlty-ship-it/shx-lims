# 启动后端 FastAPI（默认 127.0.0.1:18000；可用 BACKEND_PORT 覆盖）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$be = Join-Path $root 'backend'
Push-Location $be
try {
  if (-not (Test-Path '.\.venv')) { throw '未找到 .venv，请先运行 scripts\setup-backend.ps1' }
  $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { '18000' }
  & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port $port --reload
} finally {
  Pop-Location
}
