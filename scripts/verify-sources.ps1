. "$PSScriptRoot/common.ps1"
$lock = Get-Content (Join-Path $ProjectRoot 'sources.lock.json') -Raw | ConvertFrom-Json
foreach ($file in $lock.imports) {
    $destination = Join-Path $ProjectRoot $file.destination
    if (-not (Test-Path -LiteralPath $destination)) { throw "Missing import: $($file.destination)" }
    $hash = Get-SourceSha256 $destination
    if ($hash -ne $file.sha256) { throw "Import changed without provenance update: $($file.destination)" }
}
Write-Host "Source provenance OK: $($lock.imports.Count) unchanged imports."
$p02Manifest = Join-Path $ProjectRoot 'docs/p02-source-manifest.json'
if (Test-Path $p02Manifest) {
    $p02 = Get-Content $p02Manifest -Raw | ConvertFrom-Json
    foreach ($file in $p02 | Where-Object { $_.destination }) {
        if ((Get-SourceSha256 (Join-Path $ProjectRoot $file.destination)) -ne $file.sha256) { throw "P02 import changed: $($file.destination)" }
    }
    Write-Host 'P02 raw-byte imports verified.'
}
$p03Manifest = Join-Path $ProjectRoot 'docs/p03-source-manifest.json'
if (Test-Path $p03Manifest) {
    foreach ($file in (Get-Content $p03Manifest -Raw | ConvertFrom-Json) | Where-Object { $_.destination }) {
        if ((Get-SourceSha256 (Join-Path $ProjectRoot $file.destination)) -ne $file.sha256) { throw "P03 import changed: $($file.destination)" }
    }
    Write-Host 'P03 raw-byte reference imports verified.'
}
