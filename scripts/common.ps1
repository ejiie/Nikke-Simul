$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent

function Get-SourceSha256([string]$Path) {
    # Use the runtime directly: npm-launched PowerShell can inherit a PSModulePath
    # that omits the module containing Get-FileHash.
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
    } finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}

function Get-ProjectDotnet {
    $localDotnet = Join-Path $ProjectRoot '.tools/dotnet/dotnet.exe'
    if (Test-Path -LiteralPath $localDotnet) { return $localDotnet }
    $installed = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($installed) { return $installed.Source }
    throw 'Install the SDK pinned by global.json or run scripts/setup.ps1.'
}

function Enable-ProjectEnvironment {
    $env:DOTNET_CLI_HOME = Join-Path $ProjectRoot '.tools/dotnet-home'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_NOLOGO = '1'
    $env:NUGET_PACKAGES = Join-Path $ProjectRoot '.tools/nuget-packages'
    $env:PYTHONIOENCODING = 'utf-8'
}

function Get-ProjectPython {
    if ($env:NIKKE_PYTHON -and (Test-Path -LiteralPath $env:NIKKE_PYTHON)) { return $env:NIKKE_PYTHON }
    $bundled = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $installed = Get-Command python -ErrorAction SilentlyContinue
    if ($installed) { return $installed.Source }
    throw 'Set NIKKE_PYTHON to a Python 3 executable.'
}

function Assert-Reference {
    $lock = Get-Content (Join-Path $ProjectRoot 'sources.lock.json') -Raw | ConvertFrom-Json
    $reference = Join-Path $ProjectRoot $lock.upstream.checkout
    if (-not (Test-Path (Join-Path $reference '.git'))) { throw 'Run scripts/setup.ps1 first.' }
    $safe = $reference.Replace('\', '/')
    $head = & git -c "safe.directory=$safe" -C $reference rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head.Trim() -ne $lock.upstream.commit) { throw 'Reference commit does not match sources.lock.json.' }
    $changes = & git -c "safe.directory=$safe" -C $reference diff --name-only HEAD
    if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Reference source has changed; review and restore the pinned reference before running.' }
    return $reference
}

function Assert-GeneratedPaths([string]$SiteRoot) {
    $siteAbsolute = [IO.Path]::GetFullPath($SiteRoot)
    foreach ($relative in 'public/runtime','public/characters','dist') {
        $target = [IO.Path]::GetFullPath((Join-Path $siteAbsolute $relative))
        if (-not $target.StartsWith($siteAbsolute + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Generated path is outside the reference site: $target"
        }
        if ((Test-Path -LiteralPath $target) -and ((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Generated path must not be a reparse point: $target"
        }
    }
}
