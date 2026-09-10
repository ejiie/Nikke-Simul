[CmdletBinding()]
param([ValidateSet('build','dev')][string]$Action='build')
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$taskDotnet=Get-ProjectDotnet
$taskPython=Get-ProjectPython
$destination=Join-Path $ProjectRoot 'artifacts/desktop/win-x64'
Push-Location $ProjectRoot
try {
    $taskBrand=Join-Path $ProjectRoot 'data/local/desktop-branding/kamibot.jpg'
    if(Test-Path -LiteralPath $taskBrand){
        $taskBrandDirectory=Join-Path $ProjectRoot 'data/local/presentation/assets/ui'
        New-Item -ItemType Directory -Path $taskBrandDirectory -Force | Out-Null
        Copy-Item -LiteralPath $taskBrand -Destination (Join-Path $taskBrandDirectory 'app-icon.jpg')
    }
    & $taskPython tools/data-pipeline/account_presentation_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Account presentation assets failed.' }
    & $taskPython tools/data-pipeline/spec_presentation_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Spec presentation assets failed.' }
    foreach($item in @(@{Project='src/Nikke.Api';Output=(Join-Path $destination 'backend')},@{Project='src/Nikke.Desktop';Output=$destination})) {
        & $taskDotnet publish $item.Project -c Release -r win-x64 --self-contained true -o $item.Output --configfile nuget.config
        if ($LASTEXITCODE -ne 0) { throw 'Desktop publish failed.' }
    }
    $settings=@{projectRoot=$ProjectRoot;python=$taskPython;port=5180} | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $destination 'desktop.settings.json'),$settings,[Text.UTF8Encoding]::new($false))
    Write-Output "Desktop executable: $(Join-Path $destination 'Nikke Simul.exe')"
    if($Action -eq 'dev') { & (Join-Path $destination 'Nikke Simul.exe') }
} finally { Pop-Location }
