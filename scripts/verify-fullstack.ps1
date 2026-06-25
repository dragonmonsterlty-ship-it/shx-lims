# Full-stack verification: frontend checks, backend checks, and API smoke.
# Prerequisites: DB and backend are running; frontend dependencies are installed.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$base = if ($env:VITE_API_BASE_URL) { $env:VITE_API_BASE_URL } else { 'http://127.0.0.1:18000/api' }

Write-Host '== Frontend: typecheck / lint / test / build =='
Push-Location (Join-Path $root 'frontend')
try {
  if (-not (Test-Path '.\node_modules')) { npm install }
  npm run typecheck
  npm run lint
  npm run test
  npm run build
} finally { Pop-Location }

Write-Host '== Backend: compileall / pytest =='
Push-Location (Join-Path $root 'backend')
try {
  $py = '.\.venv\Scripts\python.exe'
  & $py -m compileall app
  $env:TEST_DATABASE_URL = 'sqlite+pysqlite:///:memory:'
  & $py -m pytest -q
} finally { Pop-Location }

Write-Host "== Full-stack smoke ($base) =="
function Invoke-Api($method, $path, $token, $body) {
  $headers = @{ Accept = 'application/json' }
  if ($token) { $headers['Authorization'] = "Bearer $token" }
  $args = @{ Method = $method; Uri = "$base$path"; Headers = $headers }
  if ($body) { $args['Body'] = ($body | ConvertTo-Json); $args['ContentType'] = 'application/json' }
  return Invoke-RestMethod @args
}
$h = Invoke-Api GET '/health'
if ($h.data.status -ne 'ok') { throw 'Health status is not ok.' }
$login = Invoke-Api POST '/auth/login' $null @{ username = 'admin'; password = 'password123' }
$tok = $login.data.access_token
if (-not $tok) { throw 'Login failed.' }
foreach ($p in @('/projects?page=1&page_size=5','/experiment-records?page=1&page_size=5','/daily-reports?page=1&page_size=5','/reagents?page=1&page_size=5','/reagent-lots?page=1&page_size=5')) {
  $r = Invoke-Api GET $p $tok
  if ($null -eq $r.data.items) { throw "List response has no items: $p" }
  Write-Host ("  OK {0} total={1}" -f $p, $r.data.total)
}
Write-Host '== T1.4 and T1.5 real business flows =='
Push-Location (Join-Path $root 'frontend')
try {
  $env:VITE_API_BASE_URL = $base
  npm run verify:api
} finally { Pop-Location }
Write-Host 'Full-stack verification passed.'
