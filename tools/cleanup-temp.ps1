param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$IncludeBuildArtifacts
)

$ErrorActionPreference = "Stop"

$targets = @(
    ".tmp",
    ".cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache"
)

$rootLegacyPatterns = @(
    ".tmp-*",
    "pytest_cache*"
)

$nestedLegacyPatterns = @(
    "pytest-cache-files-*"
)

$fileTargets = @()

if ($IncludeBuildArtifacts) {
    $targets += @(
        "build",
        "dist",
        "htmlcov"
    )
    $fileTargets += @(
        ".coverage"
    )
}

function Test-InRepo([string]$PathValue) {
    $repo = [System.IO.Path]::GetFullPath($RepoRoot)
    $candidate = [System.IO.Path]::GetFullPath($PathValue)
    return $candidate.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)
}

function Remove-RepoDirectory([string]$DirectoryPath) {
    if (-not (Test-Path -LiteralPath $DirectoryPath)) {
        return
    }
    if (-not (Test-InRepo $DirectoryPath)) {
        throw "Refusing to remove path outside repository: $DirectoryPath"
    }

    try {
        Remove-Item -LiteralPath $DirectoryPath -Recurse -Force -ErrorAction Stop
        return
    } catch {
        Write-Host "Retrying with ownership/ACL fix: $DirectoryPath"
    }

    try {
        & takeown.exe /F $DirectoryPath /R /D Y | Out-Null
    } catch {
    }
    try {
        & icacls.exe $DirectoryPath /grant "${env:USERNAME}:(OI)(CI)F" /T /C | Out-Null
    } catch {
    }
    try {
        attrib -R -S -H "$DirectoryPath" /S /D 2>$null
    } catch {
    }

    Remove-Item -LiteralPath $DirectoryPath -Recurse -Force -ErrorAction SilentlyContinue
}

function Remove-RepoFile([string]$FilePath) {
    if (-not (Test-Path -LiteralPath $FilePath)) {
        return
    }
    if (-not (Test-InRepo $FilePath)) {
        throw "Refusing to remove path outside repository: $FilePath"
    }

    Remove-Item -LiteralPath $FilePath -Force -ErrorAction SilentlyContinue
}

Write-Host "Cleaning TensorFence local artifacts under: $RepoRoot"

foreach ($target in $targets) {
    $fullPath = Join-Path $RepoRoot $target
    if (Test-Path -LiteralPath $fullPath) {
        Write-Host "Removing $fullPath"
        Remove-RepoDirectory $fullPath
    }
}

foreach ($pattern in $rootLegacyPatterns) {
    Get-ChildItem -LiteralPath $RepoRoot -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like $pattern } |
        ForEach-Object {
            Write-Host "Removing legacy temp dir $($_.FullName)"
            Remove-RepoDirectory $_.FullName
        }
}

foreach ($pattern in $nestedLegacyPatterns) {
    Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like $pattern } |
        ForEach-Object {
            Write-Host "Removing nested cache dir $($_.FullName)"
            Remove-RepoDirectory $_.FullName
        }
}

Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object {
        Write-Host "Removing python cache $($_.FullName)"
        Remove-RepoDirectory $_.FullName
    }

if ($IncludeBuildArtifacts) {
    Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*.egg-info" } |
        ForEach-Object {
            Write-Host "Removing packaging artifact $($_.FullName)"
            Remove-RepoDirectory $_.FullName
        }
}

foreach ($target in $fileTargets) {
    $fullPath = Join-Path $RepoRoot $target
    if (Test-Path -LiteralPath $fullPath) {
        Write-Host "Removing $fullPath"
        Remove-RepoFile $fullPath
    }
}

Write-Host "Cleanup finished."
