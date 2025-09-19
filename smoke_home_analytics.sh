#!/usr/bin/env bash
set -euo pipefail

# ========= Config =========
AUTH_BASE="https://aidocumines-api-layer.aidocumines.com"
BASE="$AUTH_BASE/api/v1/home-analytics"

# Superuser OAuth client + user creds (from your secrets file)
OAUTH_CLIENT_ID="EbyEjYAYUm2jYJigmnL59kXdrJWw6cOGOLm8b5fX"
OAUTH_CLIENT_SECRET="c0RIZFyeSeGVeqYLmELn3BRybuELyiJu4j2KDPgRSLn78obLZTqgbQ7v0uYlrryCM9xJkb7Ix64AgQLIhNN7vquYAXkUhTQNGgM6YeMrsfhoP7wX4fjM7S85r8n3FwU9"
ADMIN_EMAIL="admin@aidocumines.com"
ADMIN_PASSWORD="superpassword"

# If API expects the *tenant* client id in the X-Client-ID header, put it here.
# If unsure, leave empty to default to the OAuth client id.
TENANT_CLIENT_ID="${TENANT_CLIENT_ID:-}"

# Optional query params
PROJECT_ID="${PROJECT_ID:-}"
SERVICE_ID="${SERVICE_ID:-}"
SINCE_ISO="${SINCE_ISO:-}" # e.g. 2025-09-01T00:00:00Z

# ========= Helpers =========
jq_or_cat() { jq . 2>/dev/null || cat; }

hdrs() {
  local token="$1"
  local client_id_header="${TENANT_CLIENT_ID:-$OAUTH_CLIENT_ID}"
  printf '%s\n' \
    "-H" "Authorization: Bearer $token" \
    "-H" "X-Client-ID: $client_id_header" \
    "-H" "Accept: application/json"
}

qs=""
[ -n "$PROJECT_ID" ] && qs="${qs:+$qs&}project_id=$PROJECT_ID"
[ -n "$SERVICE_ID" ] && qs="${qs:+$qs&}service_id=$SERVICE_ID"
[ -n "$SINCE_ISO" ]  && qs="${qs:+$qs&}since=$SINCE_ISO"
[ -n "$qs" ] && qs="?$qs"

echo "BASE=$BASE"
echo "TENANT_CLIENT_ID=${TENANT_CLIENT_ID:-<using OAuth client id for X-Client-ID>}"
echo

# ========= 1) Get token =========
echo "### POST $AUTH_BASE/o/token/ (password grant)"
TOKEN_JSON=$(curl -sS -X POST "$AUTH_BASE/o/token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "username=$ADMIN_EMAIL" \
  --data-urlencode "password=$ADMIN_PASSWORD" \
  --data-urlencode "client_id=$OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$OAUTH_CLIENT_SECRET")
echo "$TOKEN_JSON" | jq_or_cat
ACCESS_TOKEN=$(printf '%s' "$TOKEN_JSON" | jq -r '.access_token')
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
  echo "!! Could not obtain access_token" >&2; exit 1
fi
echo

# ========= 2) Health =========
echo "### GET $BASE/health/"
curl -sS "$BASE/health/" \
  $(hdrs "$ACCESS_TOKEN") | jq_or_cat
echo

# ========= 3) Overview =========
echo "### GET $BASE/overview/$qs"
OVERVIEW_JSON=$(curl -sS "$BASE/overview/$qs" $(hdrs "$ACCESS_TOKEN"))
echo "$OVERVIEW_JSON" | jq_or_cat
echo

# ========= 4) Me (alias) =========
echo "### GET $BASE/me/$qs"
curl -sS "$BASE/me/$qs" $(hdrs "$ACCESS_TOKEN") | jq_or_cat
echo

# ========= 5) Widget-oriented probes (what our widgets actually read) =========
echo "### Probes: fields used by widgets"
printf '%s\n' "$OVERVIEW_JSON" | jq -r '
  {
    files: {
      total: .files?.total,
      new_in_window: .files?.new_in_window,
      storage_bytes: .files?.storage_bytes,
      doc_type_distribution_sample: (.files?.doc_type_distribution?[0:5] // [])
    },
    runs: {
      total: .runs?.total,
      first_status: (.runs?.by_status?[0]?.status),
      first_count:  (.runs?.by_status?[0]?.count)
    },
    search: { vector_chunks_total: .search?.vector_chunks_total },
    billing: {
      tokens_total: .billing?.tokens_total,
      last_month_tokens: (.billing?.tokens_by_month | (last.tokens? // null))
    },
    highlights_endpoints_recent_errors_len: (.highlights?.endpoints?.recent_errors | length),
    highlights_files_recent_len: (.highlights?.files?.recent | length),
    storage: .storage,
    storages_top: (.storages?[0:3] // []),
    security_keys: (.security | keys)
  }' | jq_or_cat

