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
function Invoke-ApiExpectStatus($method, $path, $token, $body, $expectedStatus) {
  $headers = @{ Accept = 'application/json' }
  if ($token) { $headers['Authorization'] = "Bearer $token" }
  $args = @{ Method = $method; Uri = "$base$path"; Headers = $headers; UseBasicParsing = $true }
  if ($body) { $args['Body'] = ($body | ConvertTo-Json); $args['ContentType'] = 'application/json' }
  try {
    $response = Invoke-WebRequest @args
    $statusCode = [int]$response.StatusCode
  } catch {
    if (-not $_.Exception.Response) { throw }
    $statusCode = [int]$_.Exception.Response.StatusCode
  }
  if ($statusCode -ne $expectedStatus) {
    throw "Expected HTTP $expectedStatus for $method $path, got $statusCode."
  }
}
function Invoke-Download($path, $token, $outFile) {
  $headers = @{ Accept = 'application/octet-stream' }
  if ($token) { $headers['Authorization'] = "Bearer $token" }
  Invoke-WebRequest -Method GET -Uri "$base$path" -Headers $headers -OutFile $outFile -UseBasicParsing
}
function Invoke-DownloadExpectStatus($path, $token, $expectedStatus) {
  $headers = @{ Accept = 'application/octet-stream' }
  if ($token) { $headers['Authorization'] = "Bearer $token" }
  try {
    $response = Invoke-WebRequest -Method GET -Uri "$base$path" -Headers $headers -UseBasicParsing
    $statusCode = [int]$response.StatusCode
  } catch {
    if (-not $_.Exception.Response) { throw }
    $statusCode = [int]$_.Exception.Response.StatusCode
  }
  if ($statusCode -ne $expectedStatus) {
    throw "Expected HTTP $expectedStatus for GET $path, got $statusCode."
  }
}
function New-StringContent($value) {
  return New-Object System.Net.Http.StringContent -ArgumentList ([string]$value)
}
function Invoke-AttachmentUpload($token, $entityType, $entityId, $fileName, $content, $contentType) {
  Add-Type -AssemblyName System.Net.Http
  $client = New-Object System.Net.Http.HttpClient
  $form = New-Object System.Net.Http.MultipartFormDataContent
  try {
    $client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue -ArgumentList 'Bearer', $token
    $form.Add((New-StringContent $entityType), 'entity_type')
    $form.Add((New-StringContent $entityId), 'entity_id')
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    $fileContent = New-Object System.Net.Http.ByteArrayContent -ArgumentList @(,$bytes)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($contentType)
    $form.Add($fileContent, 'file', $fileName)
    $response = $client.PostAsync("$base/attachments", $form).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
      throw "Attachment upload failed with HTTP $([int]$response.StatusCode): $body"
    }
    return $body | ConvertFrom-Json
  } finally {
    $form.Dispose()
    $client.Dispose()
  }
}
function Invoke-AttachmentUploadExpectStatus($token, $entityType, $entityId, $fileName, $content, $contentType, $expectedStatus) {
  Add-Type -AssemblyName System.Net.Http
  $client = New-Object System.Net.Http.HttpClient
  $form = New-Object System.Net.Http.MultipartFormDataContent
  try {
    $client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue -ArgumentList 'Bearer', $token
    $form.Add((New-StringContent $entityType), 'entity_type')
    $form.Add((New-StringContent $entityId), 'entity_id')
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    $fileContent = New-Object System.Net.Http.ByteArrayContent -ArgumentList @(,$bytes)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($contentType)
    $form.Add($fileContent, 'file', $fileName)
    $response = $client.PostAsync("$base/attachments", $form).GetAwaiter().GetResult()
    $statusCode = [int]$response.StatusCode
    if ($statusCode -ne $expectedStatus) {
      $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
      throw "Expected HTTP $expectedStatus for attachment upload, got $statusCode. $body"
    }
  } finally {
    $form.Dispose()
    $client.Dispose()
  }
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
Write-Host '== T1.6A attachment smoke =='
$managerToken = (Invoke-Api POST '/auth/login' $null @{ username = 'project_manager'; password = 'password123' }).data.access_token
$directorToken = (Invoke-Api POST '/auth/login' $null @{ username = 'director'; password = 'password123' }).data.access_token
$analystToken = (Invoke-Api POST '/auth/login' $null @{ username = 'analyst'; password = 'password123' }).data.access_token
if (-not $managerToken -or -not $directorToken -or -not $analystToken) { throw 'T1.6A smoke login failed.' }

$samples = Invoke-Api GET '/samples?page=1&page_size=20' $managerToken
$sample = $samples.data.items | Select-Object -First 1
if (-not $sample) { throw 'T1.6A smoke requires at least one manager-visible sample.' }
$sampleId = $sample.id
$content = 'T1.6A smoke attachment'
$upload = Invoke-AttachmentUpload $managerToken 'sample' $sampleId 't1-6a-smoke.txt' $content 'text/plain'
$attachmentId = $upload.data.id
if (-not $attachmentId) { throw 'T1.6A manager uploads sample attachment failed: missing attachment id.' }
Write-Host ("  OK manager uploads sample attachment id={0}" -f $attachmentId)

$listed = Invoke-Api GET "/attachments?entity_type=sample&entity_id=$sampleId" $managerToken
$found = $listed.data | Where-Object { $_.id -eq $attachmentId } | Select-Object -First 1
if (-not $found) { throw 'T1.6A list did not include uploaded attachment.' }
Write-Host '  OK list sees uploaded attachment'

$downloadPath = Join-Path ([System.IO.Path]::GetTempPath()) ("t1-6a-$attachmentId.txt")
Invoke-Download "/attachments/$attachmentId/download" $managerToken $downloadPath
$downloaded = Get-Content -Raw $downloadPath
if ($downloaded -ne $content) { throw 'T1.6A downloaded attachment content mismatch.' }
Remove-Item $downloadPath -Force
Write-Host '  OK download returns original bytes'

Invoke-AttachmentUploadExpectStatus $directorToken 'sample' $sampleId 'director-denied.txt' 'director denied' 'text/plain' 403
Write-Host '  OK director upload rejected'

$projects = Invoke-Api GET '/projects?page=1&page_size=100' $managerToken
$otherProject = $projects.data.items | Where-Object { $_.project_code -eq 'DEMO-002' } | Select-Object -First 1
if (-not $otherProject) { throw 'T1.6A smoke requires DEMO-002 project from seed data.' }
$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$crossSample = Invoke-Api POST '/samples' $managerToken @{
  project_id = $otherProject.id
  sample_no = "T16A-X-$stamp"
  name = 'T1.6A cross project sample'
  type = 'compound'
  status = 'registered'
  priority = 'normal'
}
$crossUpload = Invoke-AttachmentUpload $managerToken 'sample' $crossSample.data.id 't1-6a-cross.txt' 'cross project' 'text/plain'
$crossAttachmentId = $crossUpload.data.id
Invoke-ApiExpectStatus GET "/attachments/$crossAttachmentId" $analystToken $null 404
Invoke-DownloadExpectStatus "/attachments/$crossAttachmentId/download" $analystToken 404
Write-Host '  OK cross-project attachment access rejected'

$deleted = Invoke-Api DELETE "/attachments/$attachmentId" $managerToken $null
if (-not $deleted.data.deleted) { throw 'T1.6A delete did not return deleted=true.' }
Write-Host '  OK delete returns success'
Invoke-DownloadExpectStatus "/attachments/$attachmentId/download" $managerToken 404
Write-Host '  OK download after delete rejected'
Write-Host 'Full-stack verification passed.'
