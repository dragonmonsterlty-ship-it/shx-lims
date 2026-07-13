param(
  [Parameter(Mandatory = $true)]
  [string] $HostIP
)

$ErrorActionPreference = 'Stop'

$parsedIP = $null
if (
  -not [System.Net.IPAddress]::TryParse($HostIP, [ref] $parsedIP) -or
  $parsedIP.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
  $HostIP -eq '0.0.0.0'
) {
  throw "HostIP must be a LAN-accessible IPv4 address such as 192.168.3.50. Received: $HostIP"
}
$HostIP = $parsedIP.ToString()

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw 'docker was not found. Install and start Docker Desktop first.'
}
if (-not (Test-Path -LiteralPath $backendPython)) {
  throw 'backend\.venv was not found. Run .\scripts\setup-backend.ps1 first.'
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  throw 'npm.cmd was not found. Install Node.js first.'
}
if (-not (Get-Command pwsh.exe -ErrorAction SilentlyContinue)) {
  throw 'PowerShell 7 (pwsh.exe) was not found. Install PowerShell 7 first.'
}

$apiBase = "http://$HostIP`:18000/api"
$frontendOrigin = "http://$HostIP`:5173"
$corsOrigins = "http://localhost:5173,http://127.0.0.1:5173,$frontendOrigin"

$secretKey = $env:SECRET_KEY
if (-not $secretKey) {
  foreach ($envFile in @((Join-Path $backendDir '.env'), (Join-Path $root '.env'))) {
    if (-not (Test-Path -LiteralPath $envFile)) { continue }
    $secretLine = Get-Content -LiteralPath $envFile -Encoding UTF8 |
      Where-Object { $_ -match '^\s*SECRET_KEY\s*=' } |
      Select-Object -First 1
    if ($secretLine) {
      $secretKey = ($secretLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
      break
    }
  }
}
if (-not $secretKey -or $secretKey -eq 'change-this-development-secret') {
  throw 'SECRET_KEY must be set to a non-default value for LAN demo. Generate one with: [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))'
}

$databaseUrl = $env:DATABASE_URL
if (-not $databaseUrl) {
  foreach ($envFile in @((Join-Path $backendDir '.env'), (Join-Path $root '.env'))) {
    if (-not (Test-Path -LiteralPath $envFile)) { continue }
    $databaseLine = Get-Content -LiteralPath $envFile -Encoding UTF8 |
      Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
      Select-Object -First 1
    if ($databaseLine) {
      $databaseUrl = ($databaseLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
      break
    }
  }
}
if (-not $databaseUrl) {
  $databaseUrl = 'postgresql+psycopg://lims:lims@127.0.0.1:15432/lims'
}
$databaseUrl = $databaseUrl -replace '@localhost:15432/', '@127.0.0.1:15432/'

Push-Location $root
try {
  docker compose up -d postgres
} finally {
  Pop-Location
}

$backendCommand = @"
Set-Location -LiteralPath '$($backendDir.Replace("'", "''"))'
`$env:BACKEND_PORT = '18000'
`$env:APP_ENV = 'staging'
`$env:SECRET_KEY = '$($secretKey.Replace("'", "''"))'
`$env:CORS_ORIGINS = '$corsOrigins'
`$env:DATABASE_URL = '$($databaseUrl.Replace("'", "''"))'
& '.\.venv\Scripts\python.exe' -m alembic upgrade head
if (`$LASTEXITCODE -ne 0) { throw 'Alembic migration failed.' }
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 0.0.0.0 --port 18000
"@

$frontendCommand = @"
Set-Location -LiteralPath '$($frontendDir.Replace("'", "''"))'
`$env:VITE_API_MODE = 'real'
`$env:VITE_API_BASE_URL = '$apiBase'
if (-not (Test-Path -LiteralPath '.\node_modules')) {
  & npm.cmd install
  if (`$LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
}
& npm.cmd run dev -- --host 0.0.0.0 --port 5173
"@

Start-Process pwsh.exe -ArgumentList @(
  '-NoExit',
  '-NoProfile',
  '-ExecutionPolicy', 'Bypass',
  '-Command', $backendCommand
)
Start-Process pwsh.exe -ArgumentList @(
  '-NoExit',
  '-NoProfile',
  '-ExecutionPolicy', 'Bypass',
  '-Command', $frontendCommand
)

Write-Host ''
Write-Host 'LIMS LAN demo processes launched:'
Write-Host "  Frontend: $frontendOrigin"
Write-Host "  Backend:  $apiBase"
Write-Host '  PostgreSQL: deployment host only at 127.0.0.1:15432'
Write-Host ''
Write-Host 'Allow only TCP 5173 and 18000 through Windows Firewall.'
