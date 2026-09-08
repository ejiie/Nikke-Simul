. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$python = Get-ProjectPython
Push-Location $ProjectRoot
try {
    & $python tools/data-pipeline/prepare_runtime.py
    if ($LASTEXITCODE -ne 0) { throw 'P03 source graph preparation failed.' }
} finally { Pop-Location }
