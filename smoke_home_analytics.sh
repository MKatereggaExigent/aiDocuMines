#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Config (env vars can override these)
# ------------------------------------------------------------
BASE="${BASE:-https://aidocumines-api-layer.aidocumines.com/api/v1/home-analytics}"
CLIENT_ID="${CLIENT_ID:-3DQwq7NeVDNVavTZSqmg1oP2J8cbs8KIfyDRZcuv}"
ACCESS_TOKEN="${ACCESS_TOKEN:-REPLACE_ME}"

# Optional demo filters
SINCE_ISO="${SINCE_ISO:-2025-08-01T00:00:00Z}"
DEMO_PROJECT="${DEMO_PROJECT:-DEMO-PROJECT}"
DEMO_SERVICE="${DEMO_SERVICE:-OCR-SERVICE}"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || echo "Note: '$1' not found; output will be raw (not pretty-printed)"; }
jq_or_cat() { if command -v jq >/dev/null 2>&1; then jq .; else cat; fi; }

get() {
  local path="$1"
  echo -e "\n### GET $BASE$path"
  curl -sS \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Client-ID: $CLIENT_ID" \
    -H "Accept: application/json" \
    "$BASE$path" | jq_or_cat
}

# ------------------------------------------------------------
# Preflight
# ------------------------------------------------------------
: "${ACCESS_TOKEN:?Set ACCESS_TOKEN env var (Bearer token)}"
: "${CLIENT_ID:?Set CLIENT_ID env var (OAuth2 client_id)}"
need jq >/dev/null || true

echo "BASE=$BASE"
echo "CLIENT_ID=$CLIENT_ID"
echo "SINCE_ISO=$SINCE_ISO"
echo "DEMO_PROJECT=$DEMO_PROJECT  DEMO_SERVICE=$DEMO_SERVICE"

# ------------------------------------------------------------
# 0) Health
# ------------------------------------------------------------
get "/health/"

# ------------------------------------------------------------
# 1) Overview (alias of /me/)
# ------------------------------------------------------------
get "/overview/"
get "/me/"

# Windowing + scoping
get "/overview/?since=$SINCE_ISO"
get "/overview/?project_id=$DEMO_PROJECT&service_id=$DEMO_SERVICE"

# ------------------------------------------------------------
# 2) Sections (NOTE: /section/<key>/)
#    Available: user | files | runs | storage | search | ocr | translation |
#               operations | billing | integrations | security |
#               topics | queries | endpoints | insights | highlights
# ------------------------------------------------------------
for key in user files runs storage search ocr translation operations billing integrations security topics queries endpoints insights highlights; do
  get "/section/$key/"
done

# With filters
get "/section/ocr/?project_id=$DEMO_PROJECT"
get "/section/files/?since=$SINCE_ISO"

# ------------------------------------------------------------
# 3) Latest snapshot (if any saved)
# ------------------------------------------------------------
get "/me/snapshots/latest/"

# ------------------------------------------------------------
# 4) Cards / Timeseries / Tops
# ------------------------------------------------------------
get "/cards/"
get "/timeseries/?range=30d"
get "/top/files/?limit=5"
get "/top/searches/?limit=5"

