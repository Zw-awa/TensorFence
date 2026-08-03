#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=""
INCLUDE_BUILD_ARTIFACTS=0

for arg in "$@"; do
  case "${arg}" in
    --include-build-artifacts)
      INCLUDE_BUILD_ARTIFACTS=1
      ;;
    *)
      if [[ -z "${REPO_ROOT}" ]]; then
        REPO_ROOT="${arg}"
      else
        echo "Unexpected argument: ${arg}" >&2
        exit 1
      fi
      ;;
  esac
done

REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

echo "Cleaning TensorFence local artifacts under: ${REPO_ROOT}"

chmod -R u+rwx "${REPO_ROOT}/.cache" 2>/dev/null || true
chmod -R u+rwx "${REPO_ROOT}/.ruff_cache" 2>/dev/null || true
chmod -R u+rwx "${REPO_ROOT}/.mypy_cache" 2>/dev/null || true
chmod -R u+rwx "${REPO_ROOT}/.tmp" 2>/dev/null || true
chmod -R u+rwx "${REPO_ROOT}/.pytest_cache" 2>/dev/null || true
rm -rf "${REPO_ROOT}/.cache" || true
rm -rf "${REPO_ROOT}/.ruff_cache" || true
rm -rf "${REPO_ROOT}/.mypy_cache" || true
rm -rf "${REPO_ROOT}/.tmp" || true
rm -rf "${REPO_ROOT}/.pytest_cache" || true

find "${REPO_ROOT}" -maxdepth 1 -type d \( -name '.tmp-*' -o -name 'pytest_cache*' \) -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true
find "${REPO_ROOT}" \( -path "${REPO_ROOT}/opensource" -o -path "${REPO_ROOT}/.git" -o -path "${REPO_ROOT}/build" \) -prune -o -type d -name 'pytest-cache-files-*' -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true
find "${REPO_ROOT}" \( -path "${REPO_ROOT}/opensource" -o -path "${REPO_ROOT}/.git" -o -path "${REPO_ROOT}/build" \) -prune -o -type d -name '__pycache__' -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true

if [[ "${INCLUDE_BUILD_ARTIFACTS}" -eq 1 ]]; then
  chmod -R u+rwx "${REPO_ROOT}/build" 2>/dev/null || true
  chmod -R u+rwx "${REPO_ROOT}/dist" 2>/dev/null || true
  chmod -R u+rwx "${REPO_ROOT}/htmlcov" 2>/dev/null || true
  rm -rf "${REPO_ROOT}/build" || true
  rm -rf "${REPO_ROOT}/dist" || true
  rm -rf "${REPO_ROOT}/htmlcov" || true
  rm -f "${REPO_ROOT}/.coverage" || true
  find "${REPO_ROOT}" \( -path "${REPO_ROOT}/opensource" -o -path "${REPO_ROOT}/.git" -o -path "${REPO_ROOT}/build" \) -prune -o -type d -name '*.egg-info' -print -exec chmod -R u+rwx {} + -exec rm -rf {} + || true
fi

echo "Cleanup finished."
