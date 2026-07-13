# Full-stack verification: frontend checks, backend checks, and API smoke.
# Prerequisites: DB and backend are running; frontend dependencies are installed.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$base = if ($env:VITE_API_BASE_URL) { $env:VITE_API_BASE_URL } else { 'http://127.0.0.1:18000/api' }

function Assert-NativeExitCode($command, $exitCode) {
  if ($exitCode -ne 0) { throw "$command failed with exit code $exitCode." }
}

Write-Host '== Frontend: typecheck / lint / test / build =='
Push-Location (Join-Path $root 'frontend')
try {
  if (-not (Test-Path '.\node_modules')) {
    npm install
    Assert-NativeExitCode 'npm install' $LASTEXITCODE
  }
  npm run typecheck
  Assert-NativeExitCode 'npm run typecheck' $LASTEXITCODE
  npm run lint
  Assert-NativeExitCode 'npm run lint' $LASTEXITCODE
  npm run test
  Assert-NativeExitCode 'npm run test' $LASTEXITCODE
  npm run build
  Assert-NativeExitCode 'npm run build' $LASTEXITCODE
} finally { Pop-Location }

Write-Host '== Backend: compileall / pytest =='
Push-Location (Join-Path $root 'backend')
try {
  $py = '.\.venv\Scripts\python.exe'
  & $py -m compileall app
  Assert-NativeExitCode 'backend compileall' $LASTEXITCODE
  $env:TEST_DATABASE_URL = 'sqlite+pysqlite:///:memory:'
  & $py -m pytest -q
  Assert-NativeExitCode 'backend pytest' $LASTEXITCODE
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
  Assert-NativeExitCode 'npm run verify:api' $LASTEXITCODE
} finally { Pop-Location }
Write-Host '== T1.9.2 admin and audit RC smoke =='
$managerToken = (Invoke-Api POST '/auth/login' $null @{ username = 'project_manager'; password = 'password123' }).data.access_token
$analystToken = (Invoke-Api POST '/auth/login' $null @{ username = 'analyst'; password = 'password123' }).data.access_token
$adminUsers = Invoke-Api GET '/admin/users' $tok $null
if ($adminUsers.data -isnot [System.Array] -or $adminUsers.data.Count -lt 1) {
  throw 'RC admin user list is not a non-empty array.'
}
Write-Host '  OK admin user list'
Invoke-ApiExpectStatus GET '/admin/users' $analystToken $null 403
Write-Host '  OK non-admin user list rejected'
$adminAudit = Invoke-Api GET '/audit-logs?page=1&page_size=10' $tok $null
if ($null -eq $adminAudit.data.items -or $adminAudit.data.page_size -ne 10) {
  throw 'RC admin audit list pagination contract failed.'
}
$managerAudit = Invoke-Api GET '/audit-logs?page=1&page_size=100' $managerToken $null
if ($null -eq $managerAudit.data.items) { throw 'RC project manager audit list contract failed.' }
Invoke-ApiExpectStatus GET '/audit-logs?page=1&page_size=10' $analystToken $null 403
Write-Host '  OK ordinary member audit list rejected'
$rcExperiments = Invoke-Api GET '/experiment-records?page=1&page_size=1' $tok $null
$rcReports = Invoke-Api GET '/daily-reports?page=1&page_size=1' $tok $null
$rcSamples = Invoke-Api GET '/samples?page=1&page_size=1' $tok $null
foreach ($entity in @(
  @{ Type = 'experiment'; Id = $rcExperiments.data.items[0].id },
  @{ Type = 'daily_report'; Id = $rcReports.data.items[0].id },
  @{ Type = 'sample'; Id = $rcSamples.data.items[0].id }
)) {
  if (-not $entity.Id) { throw "RC $($entity.Type) timeline requires a real entity id." }
  $timeline = Invoke-Api GET "/audit-logs/entity/$($entity.Type)/$($entity.Id)" $tok $null
  if ($timeline.data -isnot [System.Array]) {
    throw "RC $($entity.Type) timeline is not an array."
  }
}
Write-Host '  OK experiment, daily_report, and sample entity timelines'
Write-Host '  OK cross-project entity timelines rejected by real API verifier'
Write-Host '== T1.6A attachment smoke =='
$directorToken = (Invoke-Api POST '/auth/login' $null @{ username = 'director'; password = 'password123' }).data.access_token
if (-not $managerToken -or -not $directorToken -or -not $analystToken) { throw 'T1.6A smoke login failed.' }

$projects = Invoke-Api GET '/projects?page=1&page_size=100' $managerToken
$attachmentProject = $projects.data.items | Select-Object -First 1
if (-not $attachmentProject) { throw 'T1.6A smoke requires a manager-visible project.' }
$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$sample = Invoke-Api POST '/samples' $managerToken @{
  project_id = $attachmentProject.id
  sample_no = "T16A-$stamp"
  name = 'T1.6A attachment smoke sample'
  type = 'compound'
  status = 'registered'
  priority = 'normal'
}
$sampleId = $sample.data.id
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

$adminProjects = Invoke-Api GET '/projects?page=1&page_size=100' $tok $null
$otherProject = $adminProjects.data.items | Where-Object { $_.code -like 'RC-X-*' } | Select-Object -First 1
if (-not $otherProject) { throw 'T1.6A smoke requires the isolated RC audit project.' }
$crossSample = Invoke-Api POST '/samples' $tok @{
  project_id = $otherProject.id
  sample_no = "T16A-X-$stamp"
  name = 'T1.6A cross project sample'
  type = 'compound'
  status = 'registered'
  priority = 'normal'
}
$crossUpload = Invoke-AttachmentUpload $tok 'sample' $crossSample.data.id 't1-6a-cross.txt' 'cross project' 'text/plain'
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
