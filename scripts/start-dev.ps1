$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

Write-Host "Repo: $RepoRoot"

Set-Location $RepoRoot

Write-Host "Starting infrastructure with docker compose..."
docker compose up -d

Write-Host "Starting backend on http://127.0.0.1:18000 ..."
Start-Process pwsh -ArgumentList @(
  "-NoExit",
  "-NoProfile",
  "-Command",
  "cd `"$BackendDir`"; .\.venv\Scripts\Activate.ps1; `$env:DATABASE_URL='postgresql+psycopg://lims:lims@127.0.0.1:15432/lims'; alembic upgrade head; uvicorn app.main:app --reload --host 127.0.0.1 --port 18000"
)

Write-Host "Starting frontend on http://localhost:5173 ..."
Start-Process pwsh -ArgumentList @(
  "-NoExit",
  "-NoProfile",
  "-Command",
  "cd `"$FrontendDir`"; `$env:VITE_API_BASE_URL='http://127.0.0.1:18000/api'; npm.cmd run dev -- --host 127.0.0.1 --port 5173"
)

Write-Host ""
Write-Host "LIMS dev startup launched."
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://127.0.0.1:18000/api"