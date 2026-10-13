#!/bin/bash
# LeRTX.app/Contents/MacOS/LeRTX - double-click entry point.
#
# Finds Python 3.11/3.12, stages the bundled source into a writable location
# (required because Gatekeeper may run the bundle from a read-only
# translocated path), and runs the same manage.py setup/run flow as Linux
# and Windows. Setup installs the Darwin Metal lock and does not download
# OVRTX or OVStage.
set -u

APP_SUPPORT="$HOME/Library/Application Support/LeRTX"
REPO_DIR="$APP_SUPPORT/checkout"
LOG_DIR="$HOME/Library/Logs/LeRTX"
LOG_FILE="$LOG_DIR/launcher.log"
mkdir -p "$LOG_DIR"

show_dialog() {
    # $1: message, $2: icon (stop|caution|note)
    osascript -e "display dialog \"$1\" with title \"LeRTX\" buttons {\"OK\"} default button 1 with icon $2" >/dev/null 2>&1
}

find_python() {
    local candidate
    for candidate in python3.11 python3.12; do
        if command -v "$candidate" >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done
    for candidate in \
        /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.12 \
        /usr/local/bin/python3.11 /usr/local/bin/python3.12 \
        /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

{
    echo "=== LeRTX launcher $(date) ==="

    PYTHON_BIN="$(find_python || true)"
    if [ -z "$PYTHON_BIN" ]; then
        echo "No Python 3.11/3.12 found."
        show_dialog "LeRTX needs Python 3.11 or 3.12, which was not found on this Mac.\\n\\nInstall it from python.org, or with Homebrew: brew install python@3.11\\n\\nThen relaunch LeRTX." "stop"
        exit 1
    fi
    echo "Using Python: $PYTHON_BIN"

    BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    BUNDLE_SOURCE="$BUNDLE_DIR/Resources/app"
    if [ ! -d "$REPO_DIR" ]; then
        echo "Staging bundled application into $REPO_DIR"
        mkdir -p "$APP_SUPPORT"
        cp -R "$BUNDLE_SOURCE" "$REPO_DIR"
    fi

    cd "$REPO_DIR" || exit 1

    if ! "$PYTHON_BIN" desktop/manage.py setup; then
        echo "manage.py setup failed."
        show_dialog "LeRTX could not finish setup on this Mac.\\n\\nInstall Python 3.11 or 3.12 if needed, confirm this Mac has Metal, and see ~/Library/Logs/LeRTX/launcher.log for details." "caution"
        exit 1
    fi

    exec "$PYTHON_BIN" desktop/manage.py run
} >> "$LOG_FILE" 2>&1
