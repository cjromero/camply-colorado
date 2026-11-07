#!/usr/bin/env bash
# ==============================================================================
# RUN ALL CAMPLY SCRIPTS IN BACKGROUND SCREEN SESSIONS
# ==============================================================================
# Usage:
#   ./run_all_camply.sh          # Start all camply search scripts in detached screen sessions
#   ./run_all_camply.sh --status # List running camply_* screen sessions
#   ./run_all_camply.sh --stop   # Stop all running camply_* screen sessions
#
# How it works:
#   - Scans the directory containing this script for all *.sh scripts (ignoring itself).
#   - Launches each script inside a detached GNU `screen` session named:
#       camply_<script_name>
#   - Logs output to ./logs/<script_name>.log
#   - Attach to any running session with:
#       screen -r camply_<script_name>
#     (Press Ctrl+A then D to detach without stopping it.)
# ==============================================================================

set -euo pipefail

CAMPLY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${CAMPLY_DIR}/logs"
mkdir -p "$LOG_DIR"

ACTION="${1:-start}"

if [[ "$ACTION" == "--status" || "$ACTION" == "status" ]]; then
    echo "Active camply screen sessions:"
    screen -ls | grep "camply_" || echo "  (No active camply_* screen sessions found)"
    exit 0
fi

if [[ "$ACTION" == "--stop" || "$ACTION" == "stop" ]]; then
    echo "Stopping all camply_* screen sessions..."
    for session in $(screen -ls | awk '/\.camply_/ {print $1}'); do
        echo "  Stopping $session..."
        screen -S "$session" -X quit || true
    done
    echo "Done."
    exit 0
fi

echo "Scanning ${CAMPLY_DIR} for camply search scripts..."
started=0
skipped=0

for script_path in "${CAMPLY_DIR}"/*.sh; do
    [[ -e "$script_path" ]] || continue
    script_file="$(basename "$script_path")"

    # Skip runner/utility scripts
    if [[ "$script_file" == "run_all_camply.sh" || "$script_file" == "stop_all_camply.sh" ]]; then
        continue
    fi

    # Ensure the script is executable
    chmod +x "$script_path"

    script_base="${script_file%.sh}"
    session_name="camply_${script_base}"
    log_file="${LOG_DIR}/${script_base}.log"

    # Check if a screen session with this name is already running
    if screen -ls | grep -q "\.${session_name}[[:space:]]"; then
        echo "  [SKIP] ${script_file} is already running in screen session '${session_name}'"
        skipped=$((skipped + 1))
        continue
    fi

    echo "  [START] Launching ${script_file} -> screen session '${session_name}' (log: ${log_file})"
    screen -dmS "$session_name" bash -c "'$script_path' 2>&1 | tee -a '$log_file'"
    started=$((started + 1))
done

echo ""
echo "Summary: ${started} started, ${skipped} already running."
echo "Active camply screen sessions:"
screen -ls | grep "camply_" || echo "  (None)"
echo ""
echo "Tip: Attach to a session with 'screen -r <session_name>' (detach with Ctrl+A then D)."
