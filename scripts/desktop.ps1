[CmdletBinding()]
param([ValidateSet('build','dev')][string]$Action='build')
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$taskDotnet=Get-ProjectDotnet
$taskPython=Get-ProjectPython
$destination=Join-Path $ProjectRoot 'artifacts/desktop/win-x64'
Push-Location $ProjectRoot
try {
    $generated=Join-Path $ProjectRoot 'apps/desktop-ui/generated'
    New-Item -ItemType Directory -Force -Path $generated | Out-Null
    & node apps/web/node_modules/vite/bin/vite.js build --config apps/web/vite.desktop.config.ts
    if ($LASTEXITCODE -ne 0) { throw 'Run npm --prefix apps/web ci first.' }
    foreach($item in @(@{Project='src/Nikke.Api';Output=(Join-Path $destination 'backend')},@{Project='src/Nikke.Desktop';Output=$destination})) {
        & $taskDotnet publish $item.Project -c Release -r win-x64 --self-contained true -o $item.Output --configfile nuget.config
        if ($LASTEXITCODE -ne 0) { throw 'Desktop publish failed.' }
    }
    $settings=@{projectRoot=$ProjectRoot;python=$taskPython;port=5180} | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $destination 'desktop.settings.json'),$settings,[Text.UTF8Encoding]::new($false))
    Write-Output "Desktop executable: $(Join-Path $destination 'Nikke Simul.exe')"
    if($Action -eq 'dev') { & (Join-Path $destination 'Nikke Simul.exe') }
} finally { Pop-Location }
