#!/bin/bash
# PytestDeck container entrypoint.
#
# Syncs the target repository's dependencies into a Linux virtualenv kept on a
# persistent volume (PYTESTDECK_TARGET_VENV), then starts the server.
# The sync runs in the background so the web UI is available immediately;
# the backend reports "environment preparing" until the status file says ready.
set -eo pipefail

TARGET_PATH="${TARGET_PATH:-/target}"
STATUS_FILE="${PYTESTDECK_ENV_STATUS_FILE:-/cache/env_status}"
SYNC_LOG="${PYTESTDECK_ENV_SYNC_LOG:-/cache/env_sync.log}"

mkdir -p "$(dirname "$STATUS_FILE")" "$(dirname "$SYNC_LOG")"

sync_target_env() {
    echo "running" > "$STATUS_FILE"
    echo "[PytestDeck] Syncing target dependencies into ${PYTESTDECK_TARGET_VENV:-<target .venv>} (log: $SYNC_LOG)..."
    if [ -n "${PYTESTDECK_TARGET_VENV:-}" ]; then
        export UV_PROJECT_ENVIRONMENT="$PYTESTDECK_TARGET_VENV"
    fi
    if uv sync --all-groups --directory "$TARGET_PATH" 2>&1 | tee "$SYNC_LOG"; then
        echo "ready" > "$STATUS_FILE"
        echo "[PytestDeck] Target environment ready."
    else
        echo "failed" > "$STATUS_FILE"
        echo "[PytestDeck] Target environment sync FAILED. See $SYNC_LOG:"
        tail -n 20 "$SYNC_LOG" || true
    fi
}

if [ -f "$TARGET_PATH/pyproject.toml" ]; then
    sync_target_env &
else
    echo "ready" > "$STATUS_FILE"
fi

exec "$@"
