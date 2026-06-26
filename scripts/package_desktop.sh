#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-huawei-uos-arm64}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"
RELEASE="$ROOT/release"
VENV="$ROOT/.venv"
VENV_PYTHON="$VENV/bin/python"

require_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing command: $name. $hint" >&2
    exit 1
  fi
}

case "$TARGET" in
  huawei-uos-arm64)
    TARGET_TRIPLE="aarch64-unknown-linux-gnu"
    ;;
  linux-x64)
    TARGET_TRIPLE="x86_64-unknown-linux-gnu"
    ;;
  *)
    echo "Unsupported target: $TARGET" >&2
    echo "Usage: scripts/package_desktop.sh [huawei-uos-arm64|linux-x64]" >&2
    exit 1
    ;;
esac

echo "Target platform: $TARGET"
echo "Target triple: $TARGET_TRIPLE"

require_command "$PYTHON_BIN" "Install Python 3.12, or set PYTHON_BIN to a full Python executable path."
require_command pnpm "Install pnpm."
require_command rustc "Install rustup / Rust stable."
require_command cargo "Install rustup / Cargo."

"$PYTHON_BIN" --version >/dev/null
pnpm --version >/dev/null
rustc --version >/dev/null
cargo --version >/dev/null

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Creating project virtual environment..."
  cd "$ROOT"
  "$PYTHON_BIN" -m venv .venv
fi

echo "Installing backend dependencies..."
cd "$BACKEND"
"$VENV_PYTHON" -m pip install -r requirements-sidecar.txt

echo "Installing frontend dependencies..."
cd "$FRONTEND"
pnpm install --frozen-lockfile --store-dir ../.npm-cache/pnpm-store

echo "Building Python sidecar..."
cd "$ROOT"
"$VENV_PYTHON" scripts/build_sidecar.py --target-triple "$TARGET_TRIPLE"

echo "Building Tauri desktop package..."
cd "$FRONTEND"
pnpm tauri:build

echo "Collecting release artifacts..."
case "$TARGET" in
  huawei-uos-arm64)
    RELEASE_DIR="$RELEASE/huawei-uos-arm64"
    ;;
  linux-x64)
    RELEASE_DIR="$RELEASE/linux-x64"
    ;;
esac
mkdir -p "$RELEASE_DIR"
cp "$FRONTEND/src-tauri/target/release/word-batch-workbench" "$RELEASE_DIR/格式通"
cp "$FRONTEND/src-tauri/target/release/word-batch-sidecar" "$RELEASE_DIR/word-batch-sidecar"

echo "Done. Check packages under frontend/src-tauri/target/release/bundle."
