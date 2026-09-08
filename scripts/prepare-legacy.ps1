param([string]$SourceRoot = '')
. "$PSScriptRoot/common.ps1"
$lock = Get-Content (Join-Path $ProjectRoot 'sources.lock.json') -Raw | ConvertFrom-Json
if (-not $SourceRoot) { $SourceRoot = $lock.legacy.path }
$source = [IO.Path]::GetFullPath($SourceRoot)
$target = Join-Path $ProjectRoot $lock.legacy.checkout
$manifest = Get-Content (Join-Path $ProjectRoot 'docs/legacy-source-manifest.json') -Raw | ConvertFrom-Json
# Validate all pinned sources before copying anything. Do not silently update the baseline.
foreach ($entry in $manifest) {
    $path = Join-Path $source $entry.path
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing legacy file: $($entry.path)" }
    $hash = Get-SourceSha256 $path
    if ($hash -ne $entry.sha256) { throw "Legacy source differs from P00: $($entry.path)" }
}
foreach ($entry in $manifest) {
    $destination = Join-Path $target $entry.path
    New-Item -ItemType Directory -Force (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $source $entry.path) -Destination $destination
}
'{"sdk":{"version":"8.0.407","rollForward":"disable"}}' | Set-Content (Join-Path $target 'global.json') -Encoding utf8
# Data stays in ignored local storage. Only explicitly required baseline inputs are copied.
$processed = @('burst_gauge_table.json','collection_base_table.json','collection_effect_table.json',
    'cube_base_table.json','cube_effect_table.json','equip_stat_table.json','nikke_merged_db_returned.json',
    'proper_distance_table.json','roledata_clean.json','stat_table.csv','user_state_clean.json')
$dataFiles = @($processed | ForEach-Object { "Database/processed/$_" }) + @(
    'Database/raw/staticdata/assembled/skill_chains.json',
    'Database/raw/staticdata/raid/solo_raid_boss.json')
$evidence = foreach ($relative in $dataFiles) {
    $inputPath = Join-Path $source $relative
    $destination = Join-Path $target $relative
    $present = Test-Path -LiteralPath $inputPath
    if ($present) {
        New-Item -ItemType Directory -Force (Split-Path $destination -Parent) | Out-Null
        Copy-Item -LiteralPath $inputPath -Destination $destination
        [ordered]@{ path = $relative; present = $true; sha256 = (Get-SourceSha256 $destination) }
    } else {
        if (Test-Path -LiteralPath $destination) { throw "Stale reference data exists for missing input: $relative" }
        [ordered]@{ path = $relative; present = $false }
    }
}
$evidenceDir = Join-Path $ProjectRoot 'artifacts/p00'
New-Item -ItemType Directory -Force $evidenceDir | Out-Null
$evidence | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $evidenceDir 'legacy-data-manifest.json') -Encoding utf8
Write-Host "Legacy baseline prepared: $($manifest.Count) source files; $(@($evidence | Where-Object { $_.present }).Count)/$($dataFiles.Count) data inputs present."
