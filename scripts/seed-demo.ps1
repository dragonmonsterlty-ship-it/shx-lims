param(
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot 'backend'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'

Write-Warning 'LOCAL demo/dev ONLY: this rebuilds the schema and all data for the currently configured database.'
if (-not $Force) {
  throw 'Destructive reset was not run. Verify the target is local demo/dev, then pass -Force explicitly.'
}
if (-not (Test-Path -LiteralPath $python)) {
  throw "Backend Python was not found at $python. Run .\scripts\setup-backend.ps1 first."
}

Push-Location $backendRoot
try {
  $databaseProbe = @'
from sqlalchemy.engine import make_url
from app.core.config import settings

url = make_url(settings.database_url)
print(url.drivername)
print(url.host)
print(url.port)
print(url.database)
'@
  $databaseInfoLines = @(& $python -c $databaseProbe)
  if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read the current backend database configuration.'
  }
  if ($databaseInfoLines.Count -ne 4) {
    throw 'Database configuration probe returned an unexpected result.'
  }
  $driver = [string]$databaseInfoLines[0]
  $hostName = [string]$databaseInfoLines[1]
  $port = [int]$databaseInfoLines[2]
  $databaseName = [string]$databaseInfoLines[3]

  if ($driver -notlike 'postgresql*') {
    throw "Safety guard: only local PostgreSQL may be rebuilt; current driver is '$driver'."
  }
  if ($hostName -notin @('localhost', '127.0.0.1')) {
    throw "Safety guard: database host '$hostName' is not localhost/127.0.0.1."
  }
  if ($port -ne 15432) {
    throw "Safety guard: database port '$port' is not the project local port 15432."
  }
  if ($databaseName -match '(?i)(prod|production|online|live)') {
    throw "Safety guard: database name '$databaseName' looks like a production database."
  }
  $isDefaultLocal = $databaseName -eq 'lims'
  $isExplicitDemoDev = $databaseName -match '(?i)(demo|dev|test)'
  if (-not ($isDefaultLocal -or $isExplicitDemoDev)) {
    throw "Safety guard: database '$databaseName' is neither local default 'lims' nor explicitly demo/dev/test."
  }

  Write-Host "Safety checks passed: $hostName`:$port/$databaseName"
  Write-Host 'Running: alembic downgrade base (deletes the current schema and data)'
  & $python -m alembic downgrade base
  if ($LASTEXITCODE -ne 0) { throw 'alembic downgrade base failed.' }

  Write-Host 'Running: alembic upgrade head'
  & $python -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw 'alembic upgrade head failed.' }

  & $python scripts\seed_demo.py
  if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed.' }
  Write-Host 'Local demo/dev data is ready. Continue with docs/demo-walkthrough.md.'
}
finally {
  Pop-Location
}
