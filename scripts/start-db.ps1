# 启动 PostgreSQL（docker-compose，宿主机端口 15432）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  docker compose up -d postgres
  Write-Host 'PostgreSQL 已启动：localhost:15432'
} finally {
  Pop-Location
}
