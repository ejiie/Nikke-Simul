[CmdletBinding()]
param([string]$Zip,[switch]$Refresh,[string]$DataRoot,[string]$Output)
. "$PSScriptRoot/common.ps1"
Enable-ProjectEnvironment
$taskPython=Get-ProjectPython
$taskArgs=@((Join-Path $ProjectRoot 'tools/data-pipeline/presentation_assets.py'))
if($Zip){$taskArgs+=@('--zip',$Zip)}
if($Refresh){$taskArgs+='--refresh'}
if($DataRoot){$taskArgs+=@('--data-root',$DataRoot)}
if($Output){$taskArgs+=@('--output',$Output)}
& $taskPython @taskArgs
if($LASTEXITCODE -ne 0){throw 'Presentation preparation failed.'}
