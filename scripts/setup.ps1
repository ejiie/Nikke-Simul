param([switch]$SkipSdk)
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$lock = Get-Content (Join-Path $ProjectRoot 'sources.lock.json') -Raw | ConvertFrom-Json
$reference = Join-Path $ProjectRoot $lock.upstream.checkout
if (-not (Test-Path -LiteralPath $reference)) {
    & git clone --no-checkout $lock.upstream.url $reference
    if ($LASTEXITCODE -ne 0) { throw 'Reference clone failed.' }
    & git -c "safe.directory=$($reference.Replace('\','/'))" -C $reference checkout --detach $lock.upstream.commit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned reference checkout failed.' }
}
$reference = Assert-Reference
if (-not $SkipSdk) {
    $sdk = (Get-Content (Join-Path $ProjectRoot 'global.json') -Raw | ConvertFrom-Json).sdk.version
    $toolDir = Join-Path $ProjectRoot '.tools'
    $localDotnet = Join-Path $toolDir 'dotnet/dotnet.exe'
    $hasSdk = $false
    if (Test-Path -LiteralPath $localDotnet) {
        $hasSdk = [bool]((& $localDotnet --list-sdks) -match "^$([regex]::Escape($sdk)) ")
    }
    if (-not $hasSdk) {
        New-Item -ItemType Directory -Force $toolDir | Out-Null
        $installer = Join-Path $toolDir 'dotnet-install.ps1'
        Invoke-WebRequest https://dot.net/v1/dotnet-install.ps1 -OutFile $installer -UseBasicParsing
        & $installer -Version $sdk -InstallDir (Join-Path $toolDir 'dotnet') -NoPath
        if ($LASTEXITCODE -ne 0) { throw 'SDK installation failed.' }
    }
}
Push-Location (Join-Path $reference 'site')
try {
    & npm.cmd ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Reference dependency installation failed.' }
} finally { Pop-Location }
$dotnet = Get-ProjectDotnet
Push-Location $ProjectRoot
try {
    & $dotnet restore Nikke.Simul.slnx --locked-mode --configfile nuget.config
    if ($LASTEXITCODE -ne 0) { throw 'Solution restore failed.' }
} finally { Pop-Location }
Write-Host 'Setup complete. npm test / npm run dev'
