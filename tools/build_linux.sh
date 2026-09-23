#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BUILD_DIR="$ROOT/build"
DIST_DIR="$ROOT/dist"
VENV="$BUILD_DIR/venv"
UV=${UV:-/root/.local/bin/uv}
LIBTORRENT_WHEEL_DIR=${LIBTORRENT_WHEEL_DIR:-/root/libtorrent-build/wheels}
BUILD_VERSION=${SERREBITORRENT_BUILD_VERSION:-}

if [[ ! -x "$UV" ]]; then
    echo "uv was not found: $UV" >&2
    exit 1
fi
if ! pkg-config --exists gtk+-3.0; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        libgtk-3-dev libtiff-dev libwebp-dev
fi
case "$BUILD_DIR" in "$ROOT"/*) ;; *) echo "Unsafe build path: $BUILD_DIR" >&2; exit 1 ;; esac
case "$DIST_DIR" in "$ROOT"/*) ;; *) echo "Unsafe dist path: $DIST_DIR" >&2; exit 1 ;; esac

rm -rf -- "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR"
"$UV" venv --python 3.14 "$VENV"
PYTHON="$VENV/bin/python"

mapfile -t selection < <(
    "$PYTHON" "$ROOT/tools/select_libtorrent_wheel.py" \
        --wheel-dir "$LIBTORRENT_WHEEL_DIR" \
        --platform-pattern 'manylinux.*x86_64'
)
if [[ ${#selection[@]} -ne 2 ]]; then
    echo "Could not select a Linux CPython 3.14 libtorrent wheel." >&2
    exit 1
fi
LIBTORRENT_WHEEL=${selection[0]}

"$UV" pip install --python "$PYTHON" \
    --requirement "$ROOT/requirements.txt" \
    --requirement "$ROOT/requirements-build.txt"
"$UV" pip install --python "$PYTHON" --reinstall --no-deps "$LIBTORRENT_WHEEL"
LIBTORRENT_VERSION=$(
    "$PYTHON" -c 'import libtorrent; print(libtorrent.__version__)'
)
echo "Using libtorrent $LIBTORRENT_VERSION from $LIBTORRENT_WHEEL"

if [[ -n "$BUILD_VERSION" ]]; then
    if [[ ! "$BUILD_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Invalid build version: $BUILD_VERSION" >&2
        exit 1
    fi
    "$PYTHON" "$ROOT/tools/update_version.py" \
        --path "$ROOT/app_version.py" --version "$BUILD_VERSION"
else
    BUILD_VERSION=$(
        "$PYTHON" -c \
            'from app_version import APP_VERSION; print(APP_VERSION)'
    )
fi

cd "$ROOT"
"$PYTHON" -m PyInstaller SerrebiTorrent.spec --noconfirm
"$PYTHON" tools/audit_bundle.py "dist/SerrebiTorrent"
"$PYTHON" tools/verify_frozen.py \
    "dist/SerrebiTorrent/SerrebiTorrent" \
    "build/frozen-self-test.json" \
    --expected-libtorrent "$LIBTORRENT_VERSION"

ARCHIVE="$DIST_DIR/SerrebiTorrent-v${BUILD_VERSION}-linux-x86_64.tar.gz"
tar -C "$DIST_DIR" -czf "$ARCHIVE" SerrebiTorrent
echo "Linux package: $ARCHIVE"
