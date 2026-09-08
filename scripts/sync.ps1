param([ValidateSet('setup','dev','build','test')][string]$Action = 'dev')
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$env:NIKKE_PROJECT_ROOT = $ProjectRoot
$env:NIKKE_PYTHON = Get-ProjectPython
$dotnet = Get-ProjectDotnet
Push-Location $ProjectRoot
try {
    switch ($Action) {
        'setup' {
            $reference = Assert-Reference
            & $env:NIKKE_PYTHON -m pip install -r tools/data-pipeline/requirements.txt
            if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
            $env:PATH = (Split-Path $env:NIKKE_PYTHON -Parent) + [IO.Path]::PathSeparator + $env:PATH
            Push-Location (Join-Path $reference 'site')
            try {
                Assert-GeneratedPaths (Get-Location).Path
                & npm.cmd run sync-runtime
                if ($LASTEXITCODE -ne 0) { throw 'Pinned reference catalog export failed.' }
            } finally { Pop-Location }
            & $env:NIKKE_PYTHON tools/data-pipeline/prepare_catalog.py
            if ($LASTEXITCODE -ne 0) { throw 'Run P00 setup/build first to prepare reference settings.' }
            & $env:NIKKE_PYTHON tools/data-pipeline/prepare_calculation.py
            if ($LASTEXITCODE -ne 0) { throw 'P02 calculation tables could not be prepared.' }
            & npm.cmd --prefix apps/web ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
            & $dotnet restore Nikke.Simul.slnx --locked-mode --configfile nuget.config
            if ($LASTEXITCODE -ne 0) { throw 'Locked restore failed.' }
        }
        'build' {
            & npm.cmd --prefix apps/web run build
            if ($LASTEXITCODE -ne 0) { throw 'Sync UI build failed.' }
            & $dotnet build Nikke.Simul.slnx -c Release --no-restore
            if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
        }
        'dev' {
            if (-not (Test-Path 'apps/web/dist/index.html')) { throw 'Run npm run build:sync first.' }
            & $dotnet run --project src/Nikke.Api -c Release --no-build --no-launch-profile
            if ($LASTEXITCODE -ne 0) { throw 'Backend exited with an error.' }
        }
        'test' {
            & $dotnet test tests/Nikke.Sync.Tests -c Release --no-restore
            if ($LASTEXITCODE -ne 0) { throw 'Sync tests failed.' }
            & $env:NIKKE_PYTHON -m unittest discover -s tools/data-pipeline/tests -v
            if ($LASTEXITCODE -ne 0) { throw 'Collector tests failed.' }
            & npm.cmd --prefix apps/web test
            if ($LASTEXITCODE -ne 0) { throw 'Sync UI tests failed.' }
        }
    }
} finally { Pop-Location }
