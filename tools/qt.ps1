[CmdletBinding()]
param(
    [ValidateSet("configure", "build", "run", "smoke", "deploy", "clean", "help")]
    [string]$Mode = "build",
    [string]$QtRoot,
    [string]$QtVersion,
    [switch]$AgentSafe,
    [switch]$Foreground
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$useAgentSafe = $AgentSafe.IsPresent -or [bool]$env:CODEX_THREAD_ID

function Read-DotEnv([string]$Path) {
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $values }
    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        if ($line.StartsWith("export ")) { $line = $line.Substring(7).Trim() }
        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) { continue }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($key -match '^[A-Za-z_][A-Za-z0-9_]*$') { $values[$key] = $value }
    }
    return $values
}

function Get-QtRoots {
    Get-PSDrive -PSProvider FileSystem | ForEach-Object {
        $candidate = Join-Path $_.Root "Qt"
        if (Test-Path -LiteralPath $candidate) { (Resolve-Path -LiteralPath $candidate).Path }
    }
}

function Get-QtVersions([string]$Root) {
    Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $runtime = Join-Path $_.FullName "mingw_64\bin\Qt6Core.dll"
        if (Test-Path -LiteralPath $runtime) {
            $parsed = try { [version]$_.Name } catch { [version]"0.0" }
            [pscustomobject]@{ Name = $_.Name; Parsed = $parsed }
        }
    } | Sort-Object Parsed -Descending
}

$dotEnv = Read-DotEnv (Join-Path $repoRoot ".env")
if (-not $QtRoot) {
    if ($env:QT_ROOT) { $QtRoot = $env:QT_ROOT }
    elseif ($dotEnv.ContainsKey("QT_ROOT") -and $dotEnv["QT_ROOT"]) { $QtRoot = $dotEnv["QT_ROOT"] }
}
if (-not $QtVersion) {
    if ($env:QT_VERSION) { $QtVersion = $env:QT_VERSION }
    elseif ($dotEnv.ContainsKey("QT_VERSION") -and $dotEnv["QT_VERSION"]) { $QtVersion = $dotEnv["QT_VERSION"] }
}
if (-not $QtRoot) {
    $roots = @(Get-QtRoots)
    if ($QtVersion) {
        $QtRoot = $roots | Where-Object { Test-Path -LiteralPath (Join-Path $_ "$QtVersion\mingw_64\bin\Qt6Core.dll") } | Select-Object -First 1
    } else {
        $QtRoot = $roots | Where-Object { @(Get-QtVersions $_).Count -gt 0 } | Select-Object -First 1
    }
}
if (-not $QtRoot) { throw "Qt was not found. Set QT_ROOT/QT_VERSION or create .env from .env.example." }
$QtRoot = [System.IO.Path]::GetFullPath($QtRoot)
if (-not $QtVersion) {
    $QtVersion = (Get-QtVersions $QtRoot | Select-Object -First 1).Name
}
if (-not $QtVersion) { throw "No Qt MinGW kit was found under $QtRoot" }

$qtKit = Join-Path $QtRoot "$QtVersion\mingw_64"
$qtBin = Join-Path $qtKit "bin"
$mingwDirectory = Get-ChildItem -LiteralPath (Join-Path $QtRoot "Tools") -Directory -Filter "mingw*_64" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
$cmakeDirectory = Get-ChildItem -LiteralPath (Join-Path $QtRoot "Tools") -Directory -Filter "CMake*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
if (-not $mingwDirectory) { throw "Qt MinGW tools were not found under $QtRoot\Tools" }
if (-not $cmakeDirectory) { throw "Qt CMake tools were not found under $QtRoot\Tools" }
$mingwBin = Join-Path $mingwDirectory.FullName "bin"
$cmakeExe = Join-Path $cmakeDirectory.FullName "bin\cmake.exe"
$deployExe = Join-Path $qtBin "windeployqt.exe"
$buildName = if ($useAgentSafe) { "qt-agent" } else { "qt-local" }
$buildDir = Join-Path $repoRoot "build\$buildName"
$executable = Join-Path $buildDir "bin\tensorfence_qt.exe"

function Assert-Tool([string]$Path, [string]$Name) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "$Name was not found at $Path" }
}

function Set-QtEnvironment {
    Assert-Tool $cmakeExe "CMake"
    Assert-Tool (Join-Path $mingwBin "g++.exe") "Qt MinGW"
    Assert-Tool (Join-Path $qtBin "Qt6Core.dll") "Qt runtime"
    $env:Path = "$mingwBin;$qtBin;$(Split-Path -Parent $cmakeExe);$env:Path"
}

function Configure-Qt {
    Set-QtEnvironment
    $safeValue = if ($useAgentSafe) { "ON" } else { "OFF" }
    Write-Output "[INFO] Qt kit: $qtKit"
    Write-Output "[INFO] Build directory: $buildDir"
    Write-Output "[INFO] Agent-safe CMake: $safeValue"
    & $cmakeExe -S $repoRoot -B $buildDir -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release "-DCMAKE_PREFIX_PATH=$qtKit" "-DQT_AGENT_SAFE_BUILD=$safeValue"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Build-Qt {
    Configure-Qt
    $parallel = if ($useAgentSafe) { "1" } else { [string][Math]::Max(1, [Environment]::ProcessorCount) }
    & $cmakeExe --build $buildDir --parallel $parallel
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not (Test-Path -LiteralPath $executable)) { throw "Build completed but executable was not found at $executable" }
    Write-Output "[INFO] Built: $executable"
}

function Assert-Built {
    if (-not (Test-Path -LiteralPath $executable)) { throw "TensorFence is not built. Run tools/qt.ps1 build first." }
}

function Run-Qt {
    Set-QtEnvironment
    Assert-Built
    if ($Foreground) { & $executable; exit $LASTEXITCODE }
    $process = Start-Process -FilePath $executable -WorkingDirectory (Split-Path -Parent $executable) -PassThru
    Write-Output "[INFO] Started TensorFence PID=$($process.Id)"
}

function Smoke-TestQt {
    Set-QtEnvironment
    Assert-Built
    $process = Start-Process -FilePath $executable -ArgumentList "--smoke-test" -WorkingDirectory (Split-Path -Parent $executable) -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Qt smoke test failed with exit code $($process.ExitCode)" }
    Write-Output "[INFO] Qt smoke test passed."
}

function Deploy-Qt {
    Set-QtEnvironment
    Assert-Built
    if ($useAgentSafe) { Write-Output "[INFO] Deploy skipped in agent-safe mode; run with the Qt bin directory on PATH."; return }
    Assert-Tool $deployExe "windeployqt"
    & $deployExe --qmldir (Join-Path $repoRoot "src\tensorfence\qt\app") $executable
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Clean-Qt {
    if (-not (Test-Path -LiteralPath $buildDir)) { return }
    $resolved = (Resolve-Path -LiteralPath $buildDir).Path
    $buildRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "build"))
    if (-not $resolved.StartsWith($buildRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Refusing to remove path outside the build directory: $resolved" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Write-Output "[INFO] Removed $resolved"
}

switch ($Mode) {
    "configure" { Configure-Qt }
    "build" { Build-Qt }
    "run" { Run-Qt }
    "smoke" { Smoke-TestQt }
    "deploy" { Deploy-Qt }
    "clean" { Clean-Qt }
    "help" { Write-Output "tools/qt.ps1 [configure|build|run|smoke|deploy|clean]" }
}

exit 0

