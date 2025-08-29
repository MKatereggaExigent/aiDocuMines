#!/usr/bin/env bash
set -euo pipefail

# ===== EDIT THESE TWO IF NEEDED =====
BASE="https://aidocumines-api-layer.aidocumines.com"
TOKEN="ZryKYeVSrF4ltUFwhynfuTKpAwFztK"
# ====================================

CORE="$BASE/api/v1/core/onlyoffice"
AUTH=(-H "Authorization: Bearer $TOKEN")
XCLIENT="aidocumines-angular"

json_or_echo () {
  local body="$1"
  if command -v jq >/dev/null 2>&1 && [[ "$body" =~ ^\{ ]]; then
    echo "$body" | jq .
  else
    echo "$body"
  fi
}

status_line () {
  awk 'BEGIN{RS="\r\n"} /^HTTP\//{print}' "$1" | tail -n1
}

hr () { printf -- "----------------------------------------\n"; }

echo "[1/5] Create blank DOCX"
CREATE_JSON=$(
  curl -sS -X POST \
    "${CORE}/create-docx/?project_id=demo&service_id=demo&title=TestFromCurl.docx" \
    -H "Content-Type: application/json" \
    -H "X-Client-ID: $XCLIENT" \
    "${AUTH[@]}"
)
json_or_echo "$CREATE_JSON"
FILE_ID=$(echo "$CREATE_JSON" | sed -n 's/.*"file_id":\s*\([0-9]\+\).*/\1/p' | head -n1)
if [[ -z "${FILE_ID:-}" ]]; then
  echo "!! Could not parse file_id from response. Aborting."
  exit 1
fi
echo "FILE_ID=$FILE_ID"
hr

echo "[2/5] Get editor-config"
EC_JSON=$(curl -sS "${CORE}/editor-config/?file_id=${FILE_ID}" "${AUTH[@]}")
json_or_echo "$EC_JSON"
DOC_URL=$(echo "$EC_JSON" | sed -n 's/.*"url":\s*"\([^"]*\)".*/\1/p' | head -n1)
DOC_JS=$(echo "$EC_JSON" | sed -n 's/.*"docServerApiJs":\s*"\([^"]*\)".*/\1/p' | head -n1)
echo "DOC_JS=$DOC_JS"
echo "DOC_URL=$DOC_URL"
if [[ -z "${DOC_URL:-}" ]]; then
  echo "!! Missing document.url in editor-config. Aborting."
  exit 1
fi
hr

echo "[3/5] HEAD the signed-download URL (externalized)"
# If the URL is internal like http://aidocumines_web/..., rewrite host to $BASE so you can test from your laptop.
PUBLIC_DOC_URL="$DOC_URL"
PUBLIC_DOC_URL="${PUBLIC_DOC_URL/http:\/\/aidocumines_web/$BASE}"

curl -sS -I "$PUBLIC_DOC_URL" -D /tmp/signed.hdr -o /dev/null || true
echo "--- Signed-Download status ---"
status_line /tmp/signed.hdr
hr

echo "[4/5] Convert to PDF"
curl -sS -X POST "${CORE}/convert/?file_id=${FILE_ID}&output_type=pdf" "${AUTH[@]}" \
  -H 'Accept: application/json' \
  -D /tmp/convert.hdr -o /tmp/convert.body || true

echo "--- Convert status ---"
status_line /tmp/convert.hdr
echo "--- Convert body (first 600 bytes) ---"
head -c 600 /tmp/convert.body; echo
if file /tmp/convert.body | grep -qi json; then
  echo "--- Convert JSON ---"
  cat /tmp/convert.body | (command -v jq >/dev/null 2>&1 && jq . || cat)
fi

# Quick hints
if grep -qi 'Powered by CapRover' /tmp/convert.body; then
  echo "HINT: Gateway 502 to DS or DS->API. Often DS couldn't fetch the source URL."
  echo "      The signed download currently resolves to: $DOC_URL"
  echo "      If that host isn't reachable by the DS (e.g., 'aidocumines_web'), conversions will 502."
fi
if grep -q '"error":-8' /tmp/convert.body; then
  echo "HINT: OnlyOffice reports invalid token (-8). JWT secret mismatch between DS and API."
fi
hr

echo "[5/5] (Optional) Coauthoring command relay (version)"
CMD_JSON=$(curl -sS -X POST "${CORE}/command/" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"c":"version"}' || true)
json_or_echo "$CMD_JSON"
hr

echo "Done."

