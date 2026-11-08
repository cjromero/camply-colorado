#!/usr/bin/env bash
# ==============================================================================
# STANDARDIZED CAMPLY SEARCH SCRIPT
# ==============================================================================
# Copy this file to <park_name>.sh to create a new search.
# Run `chmod +x <park_name>.sh` so `run_all_camply.sh` will automatically pick
# it up and launch it inside its own background `screen` session.
#
# Useful commands to look up IDs before editing a script:
#   camply providers
#   camply campgrounds --provider ColoradoStateParks --search "Mueller"
#   camply campgrounds --provider RecreationDotGov --state CO --search "Rocky Mountain"
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the camply executable (defaults to `camply` in PATH, or override via CAMPLY_BIN)
CAMPLY_BIN="${CAMPLY_BIN:-camply}"

# ------------------------------------------------------------------------------
# 1. PROVIDER & LOCATION SETTINGS
# ------------------------------------------------------------------------------
# Provider to search against. Common options:
#   - "ColoradoStateParks" : Colorado Parks & Wildlife (CPW / ReserveAmerica)
#   - "LarimerCounty"      : Larimer County Parks (larimercamping.com / LARC)
#   - "ReserveAmerica"     : Other ReserveAmerica state parks
#   - "RecreationDotGov"   : Federal parks/forests (USFS, NPS, BLM, Army Corps)
#   - "Yellowstone"        : Yellowstone National Park Lodges / Campgrounds
PROVIDER="ColoradoStateParks"

# Campground Facility ID(s) to search.
# You can specify one or multiple IDs separated by spaces, e.g. (50032 50022).
#   50032 = Mueller State Park (Colorado Parks and Wildlife)
#   50022 = Cherry Creek State Park (Colorado Parks and Wildlife)
CAMPGROUND_IDS=(50032)

# Optional: Recreation Area ID(s) (used if you want to search an entire region/park
# instead of specific campground IDs). Leave empty () when using CAMPGROUND_IDS.
REC_AREA_IDS=()

# Optional: Specific Campsite ID(s) if you only want specific site numbers.
# Leave empty () to search all matching campsites in the campground.
CAMPSITE_IDS=()

# ------------------------------------------------------------------------------
# 2. DATE & STAY LENGTH SETTINGS
# ------------------------------------------------------------------------------
# Search window start date (YYYY-MM-DD) — the earliest check-in / arrival date.
START_DATE="2026-11-13"

# Search window end date (YYYY-MM-DD) — the latest check-out / departure date.
END_DATE="2026-11-15"

# Minimum number of consecutive nights required at the same campsite.
# Set to 2 for a full Fri+Sat weekend stay, or 1 to match either night individually.
NIGHTS=2

# Only check weekend nights (Friday and Saturday nights)? (true / false)
WEEKENDS_ONLY=true

# Optional: Specific days of the week to search (e.g. ("Friday" "Saturday")).
# Leave empty () if using WEEKENDS_ONLY or searching all days in the window.
DAYS_OF_WEEK=()

# ------------------------------------------------------------------------------
# 3. EQUIPMENT SETTINGS (TRAILER / RV / TENT)
# ------------------------------------------------------------------------------
# Equipment type to filter by.
# Supported values for ColoradoStateParks / ReserveAmerica & RecreationDotGov:
#   "Trailer", "RV", "Tent", "Cabin", "Group"
# Set to "" (empty string) to disable equipment filtering and search all site types.
EQUIPMENT_TYPE="Trailer"

# Equipment length in feet (set to 0 if length does not matter).
EQUIPMENT_LENGTH=25

# ------------------------------------------------------------------------------
# 4. CONTINUOUS BACKGROUND POLLING & NOTIFICATION SETTINGS
# ------------------------------------------------------------------------------
# Keep running and polling continuously? (true / false)
CONTINUOUS=true

# Keep searching forever even after the first available site is found? (true / false)
# When true, camply continues running and only notifies once per unique site/date.
SEARCH_FOREVER=true

# Minutes to wait between checks (minimum allowed by camply is 5; default is 10).
POLLING_INTERVAL=10

# Notification backends to trigger when a campsite is found.
# Options: ("silent") for console/log output only, or ("email"), ("pushover"),
# ("ntfy"), ("slack"), ("telegram"), ("twilio"), ("webhook") — configured in ~/.camply.
# Multiple can be listed, e.g. ("silent" "email")
NOTIFICATIONS=("silent" "email")

# Send notifications if matching campsites are already available on the very first check? (true / false)
NOTIFY_FIRST_TRY=true

# Save found campsites to disk so restarting the script doesn't re-alert on known sites? (true / false)
OFFLINE_SEARCH=true
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}" .sh)"
OFFLINE_SEARCH_PATH="${SCRIPT_DIR}/state/${SCRIPT_NAME}_found.json"

# Enable verbose debug logging? (true / false)
DEBUG=false

# ==============================================================================
# COMMAND BUILDER (No edits needed below this line)
# ==============================================================================
mkdir -p "$(dirname "$OFFLINE_SEARCH_PATH")"

CMD=("$CAMPLY_BIN")
if [[ "$DEBUG" == "true" ]]; then
    CMD+=("--debug")
fi

CMD+=(
    "campsites"
    "--provider" "$PROVIDER"
    "--start-date" "$START_DATE"
    "--end-date" "$END_DATE"
    "--nights" "$NIGHTS"
)

for cg_id in "${CAMPGROUND_IDS[@]}"; do
    CMD+=("--campground" "$cg_id")
done

for ra_id in "${REC_AREA_IDS[@]}"; do
    CMD+=("--rec-area" "$ra_id")
done

for cs_id in "${CAMPSITE_IDS[@]}"; do
    CMD+=("--campsite" "$cs_id")
done

if [[ "$WEEKENDS_ONLY" == "true" ]]; then
    CMD+=("--weekends")
fi

for day_name in "${DAYS_OF_WEEK[@]}"; do
    CMD+=("--day" "$day_name")
done

if [[ -n "$EQUIPMENT_TYPE" ]]; then
    CMD+=("--equipment" "$EQUIPMENT_TYPE" "$EQUIPMENT_LENGTH")
fi

if [[ "$CONTINUOUS" == "true" ]]; then
    CMD+=("--continuous" "--polling-interval" "$POLLING_INTERVAL")
fi

if [[ "$SEARCH_FOREVER" == "true" ]]; then
    CMD+=("--search-forever")
fi

if [[ "$NOTIFY_FIRST_TRY" == "true" ]]; then
    CMD+=("--notify-first-try")
fi

for notif in "${NOTIFICATIONS[@]}"; do
    CMD+=("--notifications" "$notif")
done

if [[ "$OFFLINE_SEARCH" == "true" ]]; then
    CMD+=("--offline-search" "--offline-search-path" "$OFFLINE_SEARCH_PATH")
fi

echo "=================================================================="
echo "Starting camply search: ${SCRIPT_NAME}"
echo "Command: ${CMD[*]}"
echo "=================================================================="

exec "${CMD[@]}"
