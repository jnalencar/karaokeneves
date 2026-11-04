#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${KARAOKE_PYTHON:-}"

if [[ -z "$PYTHON" ]]; then
    if [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
        PYTHON="$PROJECT_DIR/venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

exec "$PYTHON" "$PROJECT_DIR/app.py"
