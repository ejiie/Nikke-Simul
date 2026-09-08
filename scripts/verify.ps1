. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$dotnet = Get-ProjectDotnet
Push-Location $ProjectRoot
try {
    & $dotnet restore Nikke.Simul.slnx --locked-mode --configfile nuget.config
    if ($LASTEXITCODE -ne 0) { throw 'Locked restore failed.' }
    & $dotnet build Nikke.Simul.slnx -c Release --no-restore
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    & $dotnet test Nikke.Simul.slnx -c Release --no-build --no-restore
    if ($LASTEXITCODE -ne 0) { throw 'Core tests failed.' }
    & $dotnet run --project tools/Nikke.Smoke -c Release --no-build
    if ($LASTEXITCODE -ne 0) { throw 'Calculation fixture failed.' }
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-sources.ps1
    if ($LASTEXITCODE -ne 0) { throw 'Source provenance check failed.' }
} finally { Pop-Location }
