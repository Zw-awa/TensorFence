param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$IncludeBuildArtifacts
)

$ErrorActionPreference = "Stop"

$directoryTargets = @(
    ".tmp",
    ".cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache"
)
$fileTargets = @()

if ($IncludeBuildArtifacts) {
    $directoryTargets += @("build", "dist", "htmlcov")
    $fileTargets += ".coverage"
}

function Test-InRepo([string]$PathValue) {
    $repo = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $candidate = [System.IO.Path]::GetFullPath($PathValue)
    return $candidate.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)
}

function Remove-RepoDirectory([string]$DirectoryPath) {
    if (-not (Test-Path -LiteralPath $DirectoryPath)) { return }
    if (-not (Test-InRepo $DirectoryPath)) {
        throw "Refusing to remove path outside repository: $DirectoryPath"
    }
    Write-Host "Removing $DirectoryPath"
    Remove-Item -LiteralPath $DirectoryPath -Recurse -Force
}

function Remove-RepoFile([string]$FilePath) {
    if (-not (Test-Path -LiteralPath $FilePath)) { return }
    if (-not (Test-InRepo $FilePath)) {
        throw "Refusing to remove path outside repository: $FilePath"
    }
    Write-Host "Removing $FilePath"
    Remove-Item -LiteralPath $FilePath -Force
}

function Get-CacheSearchRoots {
    $excluded = @("opensource", ".git", "build")
    Get-ChildItem -LiteralPath $RepoRoot -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notin $excluded }
}

Write-Host "Cleaning TensorFence local artifacts under: $RepoRoot"
Write-Host "Skipping recursive cleanup under: opensource, .git, build"

foreach ($target in $directoryTargets) {
    Remove-RepoDirectory (Join-Path $RepoRoot $target)
}
foreach ($target in $fileTargets) {
    Remove-RepoFile (Join-Path $RepoRoot $target)
}

Get-ChildItem -LiteralPath $RepoRoot -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like ".tmp-*" -or $_.Name -like "pytest_cache*" } |
    ForEach-Object { Remove-RepoDirectory $_.FullName }

foreach ($root in Get-CacheSearchRoots) {
    Get-ChildItem -LiteralPath $root.FullName -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "__pycache__" -or
            $_.Name -like "pytest-cache-files-*" -or
            ($IncludeBuildArtifacts -and $_.Name -like "*.egg-info")
        } |
        ForEach-Object { Remove-RepoDirectory $_.FullName }
}

Write-Host "Cleanup finished."
