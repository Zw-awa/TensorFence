[CmdletBinding()]
param(
    [ValidateSet('local', 'wsl')]
    [string]$Target = 'local',
    [string]$CondaEnv,
    [string]$WslDistro,
    [string]$WslCondaPath,
    [switch]$CheckEnvironments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$probe = Join-Path $PSScriptRoot 'check-test-env.py'
$cacheDir = Join-Path ([System.IO.Path]::GetTempPath()) 'tensorfence-pytest-cache'
if (-not $CheckEnvironments) { New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null }

function Test-LocalConda {
    $condaCommand = Get-Command conda -ErrorAction SilentlyContinue
    if (-not $condaCommand) { return 'missing' }
    $condaPath = $condaCommand.Source
    & $condaPath env list --json *> $null
    if ($LASTEXITCODE -ne 0) { return 'uninitialized' }
    if ($CondaEnv) {
        & $condaPath run -n $CondaEnv python --version *> $null
        if ($LASTEXITCODE -ne 0) { return 'environment-missing' }
    }
    return 'available'
}

function Test-WslConda {
    if (-not $WslDistro) { return 'not-configured' }
    & wsl -d $WslDistro -- true *> $null
    if ($LASTEXITCODE -ne 0) { return 'unavailable' }
    if (-not $WslCondaPath) {
        & wsl -d $WslDistro -- sh -lc 'command -v conda >/dev/null || test -x "$HOME/miniforge3/bin/conda" || test -x "$HOME/miniconda3/bin/conda"' *> $null
        if ($LASTEXITCODE -ne 0) { return 'missing' }
        return 'path-not-configured'
    }
    & wsl -d $WslDistro -- test -x $WslCondaPath *> $null
    if ($LASTEXITCODE -ne 0) { return 'missing' }
    if ($CondaEnv) {
        & wsl -d $WslDistro -- $WslCondaPath run -n $CondaEnv python --version *> $null
        if ($LASTEXITCODE -ne 0) { return 'environment-missing' }
    }
    return 'available'
}

if ($CheckEnvironments) {
    if (-not $CondaEnv) { $CondaEnv = 'tensorfence' }
    $localState = Test-LocalConda
    $wslState = Test-WslConda
    Write-Output "Local Conda ($CondaEnv): $localState"
    if ($WslDistro) { Write-Output "WSL Conda ($WslDistro / $CondaEnv): $wslState" }
    else { Write-Output "WSL Conda: not-configured (set per-host target in .tensorfence/targets.yaml)" }
    exit 0
}

if ($Target -eq 'local') {
    if (-not $CondaEnv) { $CondaEnv = 'tensorfence' }
    $localState = Test-LocalConda
    if ($localState -ne 'available') {
        throw "Local Conda state is '$localState'. Install/initialize Conda and create the environment with: conda env create -f environment.yml"
    }
    $conda = (Get-Command conda -ErrorAction Stop).Source
    & $conda run --no-capture-output -n $CondaEnv python $probe
    if ($LASTEXITCODE -ne 0) { throw "Conda environment '$CondaEnv' is missing or incomplete. Check environment.yml." }
    & $conda run --no-capture-output -n $CondaEnv python -m pytest -o "cache_dir=$cacheDir" $repoRoot/tests
    exit $LASTEXITCODE
}

if (-not $CondaEnv -or -not $WslDistro -or -not $WslCondaPath) {
    throw 'WSL requires -WslDistro, -WslCondaPath, and -CondaEnv from your local .tensorfence/targets.yaml.'
}
$wslState = Test-WslConda
if ($wslState -ne 'available') {
    throw "WSL Conda state is '$wslState'. Install/initialize Conda in that distro and create the environment with: conda env create -f environment.wsl.yml"
}
$wslRepo = (& wsl -d $WslDistro -- wslpath -a $repoRoot).Trim()
if ($LASTEXITCODE -ne 0 -or -not $wslRepo) { throw "Cannot access repository from WSL distro '$WslDistro'." }
$wslProbe = "$wslRepo/tools/check-test-env.py"
& wsl -d $WslDistro -- $WslCondaPath run --no-capture-output -n $CondaEnv python $wslProbe
if ($LASTEXITCODE -ne 0) { throw "WSL Conda environment '$CondaEnv' is missing or incomplete. Check environment.wsl.yml." }
& wsl -d $WslDistro -- $WslCondaPath run --no-capture-output -n $CondaEnv python -m pytest -o "cache_dir=/tmp/tensorfence-pytest-cache" "$wslRepo/tests"
exit $LASTEXITCODE
