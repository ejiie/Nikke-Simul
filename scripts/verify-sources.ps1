. "$PSScriptRoot/common.ps1"
$lock = Get-Content (Join-Path $ProjectRoot 'sources.lock.json') -Raw | ConvertFrom-Json
foreach ($file in $lock.imports) {
    $destination = Join-Path $ProjectRoot $file.destination
    if (-not (Test-Path -LiteralPath $destination)) { throw "Missing import: $($file.destination)" }
    $hash = Get-SourceSha256 $destination
    if ($hash -ne $file.sha256) { throw "Import changed without provenance update: $($file.destination)" }
}
Write-Host "Source provenance OK: $($lock.imports.Count) unchanged imports."
