[CmdletBinding()]
param([string]$Zip,[switch]$Refresh)
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$taskPython=Get-ProjectPython
$taskArgs=@((Join-Path $ProjectRoot 'tools/data-pipeline/presentation_assets.py'))
if($Zip){$taskArgs+=@('--zip',$Zip)}
if($Refresh){$taskArgs+='--refresh'}
& $taskPython @taskArgs
if($LASTEXITCODE -ne 0){throw 'Presentation preparation failed.'}
