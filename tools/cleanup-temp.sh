#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

echo "Cleaning TensorFence temp/cache directories under: ${REPO_ROOT}"

chmod -R u+rwx "${REPO_ROOT}/.tmp" 2>/dev/null || true
chmod -R u+rwx "${REPO_ROOT}/.pytest_cache" 2>/dev/null || true
rm -rf "${REPO_ROOT}/.tmp" || true
rm -rf "${REPO_ROOT}/.pytest_cache" || true

find "${REPO_ROOT}" -maxdepth 1 -type d \( -name '.tmp-*' -o -name 'pytest-cache-files-*' -o -name 'pytest_cache*' \) -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true
find "${REPO_ROOT}" -type d -name '__pycache__' -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true

echo "Cleanup finished."
