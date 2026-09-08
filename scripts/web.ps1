param([ValidateSet('dev','build','test','check')][string]$Action = 'dev')
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$reference = Assert-Reference
$site = Join-Path $reference 'site'
Assert-GeneratedPaths $site
$python = Get-ProjectPython
$env:PATH = (Split-Path $python -Parent) + [IO.Path]::PathSeparator + $env:PATH
# Whitespace survives Windows environment propagation and is trimmed to disabled by upstream.
# This local reference must not use the upstream author's profile/share/presence services.
$env:VITE_BLABLA_PROXY = ' '
$env:VITE_SHARE_API = ' '
Write-Host 'P00 reference UI: upstream Python engine; new C# combat backend is not connected.'
Push-Location $site
try {
    switch ($Action) {
        'dev'   { & npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort }
        'build' { & npm.cmd run build }
        'test'  { & npm.cmd test -- --run --maxWorkers=2 --testTimeout=30000 }
        'check' { & npm.cmd run check-pages }
    }
    if ($LASTEXITCODE -ne 0) { throw "Reference web $Action failed ($LASTEXITCODE)." }
} finally { Pop-Location }
