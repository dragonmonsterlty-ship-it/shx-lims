# 全栈验证：前端三检+单测、后端 compileall+pytest、全栈 smoke
# 前置：DB 已启动、后端已 setup 并在运行（默认 18000）、前端已 npm install。
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$base = if ($env:VITE_API_BASE_URL) { $env:VITE_API_BASE_URL } else { 'http://127.0.0.1:18000/api' }

Write-Host '== 前端：typecheck / lint / test / build =='
Push-Location (Join-Path $root 'frontend')
try {
  if (-not (Test-Path '.\node_modules')) { npm install }
  npm run typecheck
  npm run lint
  npm run test
  npm run build
} finally { Pop-Location }

Write-Host '== 后端：compileall / pytest =='
Push-Location (Join-Path $root 'backend')
try {
  $py = '.\.venv\Scripts\python.exe'
  & $py -m compileall app
  $env:TEST_DATABASE_URL = 'sqlite+pysqlite:///:memory:'
  & $py -m pytest -q
} finally { Pop-Location }

Write-Host "== 全栈 smoke（$base）=="
function Invoke-Api($method, $path, $token, $body) {
  $headers = @{ Accept = 'application/json' }
  if ($token) { $headers['Authorization'] = "Bearer $token" }
  $args = @{ Method = $method; Uri = "$base$path"; Headers = $headers }
  if ($body) { $args['Body'] = ($body | ConvertTo-Json); $args['ContentType'] = 'application/json' }
  return Invoke-RestMethod @args
}
$h = Invoke-Api GET '/health'
if ($h.data.status -ne 'ok') { throw 'health 非 ok' }
$login = Invoke-Api POST '/auth/login' $null @{ username = 'admin'; password = 'password123' }
$tok = $login.data.access_token
if (-not $tok) { throw '登录失败' }
foreach ($p in @('/projects?page=1&page_size=5','/experiment-records?page=1&page_size=5','/daily-reports?page=1&page_size=5','/reagents?page=1&page_size=5','/reagent-lots?page=1&page_size=5')) {
  $r = Invoke-Api GET $p $tok
  if ($null -eq $r.data.items) { throw "列表无 items: $p" }
  Write-Host ("  OK {0} total={1}" -f $p, $r.data.total)
}
Write-Host '全栈验证通过。'
