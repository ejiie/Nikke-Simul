param([Parameter(Mandatory=$true)][string]$Baseline)
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$taskDotnet=Get-ProjectDotnet
$taskBaseline=(Resolve-Path -LiteralPath $Baseline).Path
Push-Location $ProjectRoot
try {
    & $taskDotnet restore tools/connection-audit/ConnectionAudit.csproj --configfile nuget.config --locked-mode
    if ($LASTEXITCODE -ne 0) { throw 'Connection audit restore failed.' }
    & $taskDotnet run --no-restore --project tools/connection-audit/ConnectionAudit.csproj -c Release -- $ProjectRoot $taskBaseline
    if ($LASTEXITCODE -ne 0) { throw 'Connection audit failed.' }
} finally { Pop-Location }
