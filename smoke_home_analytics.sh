#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Config — override any via environment variables
# ============================================================
AUTH_BASE="${AUTH_BASE:-https://aidocumines-api-layer.aidocumines.com}"
BASE="${BASE:-$AUTH_BASE/api/v1/home-analytics}"

# Where to read superuser OAuth creds from
SECRETS_JSON="${SECRETS_JSON:-logs/.superuser_secrets.json}"

# OAuth client + user creds (used only if ACCESS_TOKEN is not provided)
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

# Header client id — what the API expects in "X-Client-ID"
# If not provided, falls back to OAUTH_CLIENT_ID after we know it.
TENANT_CLIENT_ID="${TENANT_CLIENT_ID:-}"

# If you already have a valid token, set ACCESS_TOKEN and we skip /o/token/
ACCESS_TOKEN="${ACCESS_TOKEN:-}"

# Optional scoping / filters
SINCE_ISO="${SINCE_ISO:-}"     # e.g. 2025-08-01T00:00:00Z
PROJECT_ID="${PROJECT_ID:-}"   # e.g. DEMO-PROJECT
SERVICE_ID="${SERVICE_ID:-}"   # e.g. OCR-SERVICE

# ============================================================
# Helpers
# ============================================================
has() { command -v "$1" >/dev/null 2>&1; }
jq_or_cat() { if has jq; then jq .; else cat; fi; }
err() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "Note: $*" >&2; }

# Read a key from JSON file using jq; if permission denied, retry with sudo
read_secret() {
  local file="$1" key="$2"
  if has jq; then
    if [ -r "$file" ]; then
      jq -r ".$key" "$file"
    else
      sudo sh -c "cat '$file'" | jq -r ".$key"
    fi
  else
    err "jq is required to read secrets. Install jq or export creds via env vars."
  fi
}

hdrs() {
  local token="$1"
  local client_id_header="${TENANT_CLIENT_ID:-$OAUTH_CLIENT_ID}"
  printf '%s\n' \
    -H "Authorization: Bearer $token" \
    -H "X-Client-ID: $client_id_header" \
    -H "Accept: application/json"
}

# build query string
qs=""
[ -n "$PROJECT_ID" ] && qs="${qs:+$qs&}project_id=$PROJECT_ID"
[ -n "$SERVICE_ID" ] && qs="${qs:+$qs&}service_id=$SERVICE_ID"
[ -n "$SINCE_ISO" ]  && qs="${qs:+$qs&}since=$SINCE_ISO"
[ -n "$qs" ] && qs="?$qs"

get() {
  local path="$1"
  echo -e "\n### GET $BASE$path"
  # IMPORTANT: do NOT quote the header expansion
  curl -sS "$BASE$path" $(hdrs "$ACCESS_TOKEN") | jq_or_cat
}

get_raw() {
  # IMPORTANT: do NOT quote the header expansion
  curl -sS "$BASE$1" $(hdrs "$ACCESS_TOKEN")
}

# ============================================================
# Preflight
# ============================================================
echo "AUTH_BASE        = $AUTH_BASE"
echo "BASE             = $BASE"
echo "SECRETS_JSON     = $SECRETS_JSON"
echo "TENANT_CLIENT_ID = ${TENANT_CLIENT_ID:-<will use OAUTH_CLIENT_ID>}"
echo "PROJECT_ID       = ${PROJECT_ID:-<none>}"
echo "SERVICE_ID       = ${SERVICE_ID:-<none>}"
echo "SINCE_ISO        = ${SINCE_ISO:-<none>}"
echo

# ============================================================
# Obtain ACCESS_TOKEN if not provided
# ============================================================
if [ -z "$ACCESS_TOKEN" ]; then
  [ -n "$OAUTH_CLIENT_ID" ]     || OAUTH_CLIENT_ID="$(read_secret "$SECRETS_JSON" "client_id")"
  [ -n "$OAUTH_CLIENT_SECRET" ] || OAUTH_CLIENT_SECRET="$(read_secret "$SECRETS_JSON" "client_secret")"
  [ -n "$ADMIN_EMAIL" ]         || ADMIN_EMAIL="$(read_secret "$SECRETS_JSON" "admin_email")"
  [ -n "$ADMIN_PASSWORD" ]      || ADMIN_PASSWORD="$(read_secret "$SECRETS_JSON" "admin_password")"

  [ -n "$OAUTH_CLIENT_ID" ]     || err "Missing OAUTH_CLIENT_ID"
  [ -n "$OAUTH_CLIENT_SECRET" ] || err "Missing OAUTH_CLIENT_SECRET"
  [ -n "$ADMIN_EMAIL" ]         || err "Missing ADMIN_EMAIL"
  [ -n "$ADMIN_PASSWORD" ]      || err "Missing ADMIN_PASSWORD"

  echo "### POST $AUTH_BASE/o/token/ (password grant)"
  TOKEN_JSON=$(
    curl -sS -X POST "$AUTH_BASE/o/token/" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data-urlencode "grant_type=password" \
      --data-urlencode "username=$ADMIN_EMAIL" \
      --data-urlencode "password=$ADMIN_PASSWORD" \
      --data-urlencode "client_id=$OAUTH_CLIENT_ID" \
      --data-urlencode "client_secret=$OAUTH_CLIENT_SECRET"
  )
  echo "$TOKEN_JSON" | jq_or_cat
  ACCESS_TOKEN="$(printf '%s' "$TOKEN_JSON" | { jq -r '.access_token' 2>/dev/null || echo ""; })"
  [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ] || err "Could not obtain access_token from /o/token/"

  if [ -z "$TENANT_CLIENT_ID" ]; then
    TENANT_CLIENT_ID="$OAUTH_CLIENT_ID"
  fi
fi

echo
echo "Using ACCESS_TOKEN = <redacted>"
echo "Header X-Client-ID = ${TENANT_CLIENT_ID:-$OAUTH_CLIENT_ID}"
echo

# ============================================================
# 0) Health
# ============================================================
get "/health/"

# ============================================================
# 1) Overview + alias (with and without filters)
# ============================================================
get "/overview/"
get "/me/"
[ -n "$qs" ] && get "/overview/$qs"

# ============================================================
# 2) Sections (baseline sweep)
# ============================================================
SECTIONS=(user files runs storage search ocr translation operations billing integrations security topics queries endpoints insights highlights)
for key in "${SECTIONS[@]}"; do
  get "/section/$key/"
done

# Filtered examples
[ -n "$PROJECT_ID" ] && get "/section/ocr/?project_id=$PROJECT_ID"
[ -n "$SINCE_ISO" ]  && get "/section/files/?since=$SINCE_ISO"

# ============================================================
# 3) Snapshots / Cards / Timeseries / Tops
# ============================================================
get "/me/snapshots/latest/"
get "/cards/"
get "/timeseries/?range=30d"
get "/top/files/?limit=5"
get "/top/searches/?limit=5"

# ============================================================
# 4) Widget Probes (from /overview/)
# ============================================================
echo -e "\n### Probes: fields used by widgets (from /overview/)"
OVERVIEW_JSON="$(get_raw "/overview/$qs")"
if has jq; then
  echo "$OVERVIEW_JSON" | jq -r '
    {
      files: {
        total: .files?.total,
        new_in_window: .files?.new_in_window,
        storage_bytes: .files?.storage_bytes,
        doc_type_distribution_len: (.files?.doc_type_distribution | length)
      },
      runs: {
        total: .runs?.total,
        first_status: (.runs?.by_status?[0]?.status),
        first_count:  (.runs?.by_status?[0]?.count)
      },
      search: { vector_chunks_total: .search?.vector_chunks_total },
      billing: {
        tokens_total: .billing?.tokens_total,
        tokens_by_month_len: (.billing?.tokens_by_month | length),
        tokens_last_month: (.billing?.tokens_by_month | last | .tokens?)
      },
      highlights: {
        endpoints_recent_errors_len: (.highlights?.endpoints?.recent_errors | length),
        files_recent_len: (.highlights?.files?.recent | length),
        storage_growth_30d_len: (.highlights?.storage_growth_30d | length)
      },
      storage_section: .storage,
      storages_array_len: (.storages | length),
      security_keys: (.security | keys)
    }'
else
  note "Install jq to see widget probes; printing raw /overview/ instead"
  echo "$OVERVIEW_JSON"
fi

# ============================================================
# 5) Quick checks table
# ============================================================
if has jq; then
  echo -e "\n### Quick checks:"
  echo "$OVERVIEW_JSON" | jq -r '
    [
      { check:"files.total present", ok:(.files?.total != null) },
      { check:"runs.total present", ok:(.runs?.total != null) },
      { check:"search.vector_chunks_total present", ok:(.search?.vector_chunks_total != null) },
      { check:"billing.tokens_total present", ok:(.billing?.tokens_total != null) },
      { check:"files.doc_type_distribution present", ok:(.files?.doc_type_distribution != null and (.files.doc_type_distribution|length) > 0) },
      { check:"highlights.endpoints.recent_errors present", ok:(.highlights?.endpoints?.recent_errors != null and (.highlights.endpoints.recent_errors|length) >= 0) },
      { check:"storages array present (for table)", ok:(.storages != null and (.storages|length) >= 0) }
    ]
    | (["check","ok"], ["-----","--"]) as $hdr
    | $hdr, (.[] | [ .check, (if .ok then "yes" else "no" end) ])
    | @tsv
  ' | column -t
fi

echo -e "\nDone."

