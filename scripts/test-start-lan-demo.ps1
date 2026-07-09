$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot 'start-lan-demo.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Missing LAN demo launcher: $scriptPath"
}

$content = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
$requiredPatterns = @(
  'param\s*\(',
  '\[string\]\s*\$HostIP',
  'VITE_API_BASE_URL',
  'http://\$HostIP`:18000/api',
  'CORS_ORIGINS',
  'http://\$HostIP`:5173',
  'Get-Command pwsh\.exe',
  'Start-Process pwsh\.exe',
  "APP_ENV = 'staging'",
  'SECRET_KEY',
  'change-this-development-secret',
  'DATABASE_URL',
  '127\.0\.0\.1',
  '--host\s+0\.0\.0\.0',
  '--port\s+18000',
  '--host\s+0\.0\.0\.0',
  '--port\s+5173'
)

foreach ($pattern in $requiredPatterns) {
  if ($content -notmatch $pattern) {
    throw "LAN demo launcher is missing required pattern: $pattern"
  }
}

Write-Host 'LAN demo launcher contract passed.'
