#!/usr/bin/env bash
set -euo pipefail

# =========================
# API base
# =========================
BASE="${BASE:-https://aidocumines-api-layer.aidocumines.com}"
CORE="$BASE/api/v1/core/onlyoffice"

# =========================
# OAuth2 creds (defaults = the ones you gave)
# Override any of these via env vars if needed.
# =========================
OAUTH_USERNAME="${OAUTH_USERNAME:-admin@aidocumines.com}"
OAUTH_PASSWORD="${OAUTH_PASSWORD:-superpassword}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-3DQwq7NeVDNVavTZSqmg1oP2J8cbs8KIfyDRZcuv}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-S5bMEDhAvABCBJLnDDW2uiTGPdsF640eRua2F9xTlI8yXTEZLjSdOdWUVxSzrZd6rY5BmyqBEoOoHAUFTwcJIBEpR8uQjiUBBL1DGvL08OBWDMYOU81E1DSXZ8qXoKO0}"

# =========================
# Optional: DS JWT secret to run direct DS checks
# export OO_SECRET='eXvZXLA4PvapRjJPrlqO4311mtFzGXux'
# =========================
OO_SECRET="${OO_SECRET:-}"

# =========================
# Client ID header your API expects
# (create-docx uses this; upload would also use X-Client-Secret)
# =========================
XCLIENT="${XCLIENT:-aidocumines-angular}"

CURL_COMMON=(-sS --retry 2 --retry-delay 1)

json_or_echo () {
  local body="$1"
  if command -v jq >/dev/null 2>&1 && [[ "$body" =~ ^\{ ]]; then
    echo "$body" | jq .
  else
    echo "$body"
  fi
}

jq_get () {
  local json="$1" path="$2"
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r "$path"
  else
    case "$path" in
      .file_id) echo "$json" | sed -n 's/.*"file_id":[[:space:]]*\([0-9]\+\).*/\1/p' | head -n1 ;;
      .config.document.url) echo "$json" | sed -n 's/.*"url":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1 ;;
      .config.document.title) echo "$json" | sed -n 's/.*"title":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1 ;;
      .docServerApiJs) echo "$json" | sed -n 's/.*"docServerApiJs":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1 ;;
      *) echo "" ;;
    esac
  fi
}

status_line () { awk 'BEGIN{RS="\r\n"} /^HTTP\//{print}' "$1" | tail -n1; }
hr () { printf -- "----------------------------------------\n"; }

url_base () {
  python3 - "$1" <<'PY' 2>/dev/null || echo ""
import sys, urllib.parse as u
p = u.urlparse(sys.argv[1])
print(f"{p.scheme}://{p.netloc}")
PY
}

mask () { # mask tokens in echo
  local s="${1:-}"; if [ -z "$s" ]; then echo ""; else echo "${s:0:6}…${s: -4}"; fi
}

echo "[0/7] Fetch OAuth2 access token"
TOK_JSON="$(
  curl "${CURL_COMMON[@]}" -X POST "$BASE/o/token/" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "username=${OAUTH_USERNAME}" \
    -d "password=${OAUTH_PASSWORD}" \
    -d "client_id=${OAUTH_CLIENT_ID}" \
    -d "client_secret=${OAUTH_CLIENT_SECRET}"
)"
ACCESS="$(jq_get "$TOK_JSON" .access_token)"
if [[ -z "${ACCESS:-}" || "${ACCESS}" == "null" ]]; then
  echo "!! Failed to get access token. Raw response:"
  json_or_echo "$TOK_JSON"
  exit 1
fi
echo "ACCESS=$(mask "$ACCESS")"
AUTH=(-H "Authorization: Bearer $ACCESS")
hr

echo "[1/7] Create blank DOCX"
CREATE_JSON=$(
  curl "${CURL_COMMON[@]}" -X POST \
    "${CORE}/create-docx/?project_id=demo&service_id=demo&title=TestFromCurl.docx" \
    -H "Content-Type: application/json" \
    -H "X-Client-ID: $XCLIENT" \
    "${AUTH[@]}"
)
json_or_echo "$CREATE_JSON"
FILE_ID="$(jq_get "$CREATE_JSON" .file_id)"
if [[ -z "${FILE_ID:-}" ]]; then
  echo "!! Could not parse file_id. Aborting."
  exit 1
fi
echo "FILE_ID=$FILE_ID"
hr

echo "[2/7] Get editor-config"
EC_JSON=$(curl "${CURL_COMMON[@]}" "${CORE}/editor-config/?file_id=${FILE_ID}" "${AUTH[@]}" -H "Accept: application/json")
json_or_echo "$EC_JSON"
DOC_URL="$(jq_get "$EC_JSON" .config.document.url)"
DOC_TITLE="$(jq_get "$EC_JSON" .config.document.title)"
DOC_JS="$(jq_get "$EC_JSON" .docServerApiJs)"
DS_BASE="$(url_base "$DOC_JS")"
echo "DOC_JS=$DOC_JS"
echo "DOC_URL=$DOC_URL"
echo "DS_BASE=$DS_BASE"
if [[ -z "${DOC_URL:-}" ]]; then
  echo "!! Missing document.url in editor-config. Aborting."
  exit 1
fi
hr

echo "[3/7] HEAD the signed-download URL (externalized) & api.js"
PUBLIC_DOC_URL="${DOC_URL/http:\/\/aidocumines_web/$BASE}"

curl "${CURL_COMMON[@]}" -I "$PUBLIC_DOC_URL" -D /tmp/signed.hdr -o /dev/null || true
echo "--- Signed-Download status ---"
status_line /tmp/signed.hdr

if [[ -n "$DOC_JS" ]]; then
  curl "${CURL_COMMON[@]}" -I "$DOC_JS" -D /tmp/api_js.hdr -o /dev/null || true
  echo "--- api.js status ---"
  status_line /tmp/api_js.hdr
fi
hr

echo "[4/7] Convert to PDF via API"
curl "${CURL_COMMON[@]}" -X POST "${CORE}/convert/?file_id=${FILE_ID}&output_type=pdf" "${AUTH[@]}" \
  -H 'Accept: application/json' \
  -D /tmp/convert.hdr -o /tmp/convert.body || true

echo "--- Convert status ---"
status_line /tmp/convert.hdr
echo "--- Convert body (first 600 bytes) ---"
head -c 600 /tmp/convert.body; echo
if file /tmp/convert.body | grep -qi json; then
  echo "--- Convert JSON ---"
  (command -v jq >/dev/null 2>&1 && jq . /tmp/convert.body) || cat /tmp/convert.body
fi

if grep -qi 'Powered by CapRover' /tmp/convert.body; then
  echo "HINT: 502 gateway—network path between API↔DS or DS↔API source download."
fi
if grep -q '"error":-8' /tmp/convert.body; then
  echo "HINT: OnlyOffice invalid token (-8). JWT secret mismatch."
fi
if grep -q '"error":-4' /tmp/convert.body; then
  echo "HINT: DS error -4 from /converter — try /ConvertService.ashx path."
fi
hr

echo "[5/7] Coauthoring command relay (version)"
CMD_JSON=$(curl "${CURL_COMMON[@]}" -X POST "${CORE}/command/" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"c":"version"}' || true)
json_or_echo "$CMD_JSON"
hr

echo "[6/7] Direct DS test: /converter (JWT in body)"
if [[ -z "${OO_SECRET}" ]]; then
  echo "Skipped (set OO_SECRET to enable)."
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Skipped (python3 not found)."
  else
    TK_JSON="$(OO_SECRET="$OO_SECRET" SD_URL="$PUBLIC_DOC_URL" DOC_TITLE="$DOC_TITLE" python3 - <<'PY'
import os,time,uuid,json,hmac,hashlib,base64
sec=os.environ["OO_SECRET"]; url=os.environ["SD_URL"]; title=os.environ["DOC_TITLE"]
key=str(uuid.uuid4()); now=int(time.time())
claims={"filetype":"docx","outputtype":"pdf","key":key,"title":title,"url":url,"iat":now,"exp":now+300}
b64=lambda b: base64.urlsafe_b64encode(b).rstrip(b'=')
hdr=b64(b'{"alg":"HS256","typ":"JWT"}')
pld=b64(json.dumps(claims,separators=(',',':')).encode())
sig=b64(hmac.new(sec.encode(), hdr+b'.'+pld, hashlib.sha256).digest())
print(json.dumps({"token":(hdr+b'.'+pld+b'.'+sig).decode(),"key":key}))
PY
)"
    BODY_TOKEN="$(jq_get "$TK_JSON" .token)"
    BODY_KEY="$(jq_get "$TK_JSON" .key)"
    [[ -z "$DS_BASE" ]] && DS_BASE="$(url_base "$DOC_JS")"
    [[ -z "$DS_BASE" ]] && DS_BASE="https://onlyoffice.aidocumines.com"

    curl "${CURL_COMMON[@]}" --max-time 300 -X POST "${DS_BASE}/converter" \
      -H "Content-Type: application/json" \
      -d '{
        "async": false,
        "filetype": "docx",
        "outputtype": "pdf",
        "key": "'"$BODY_KEY"'",
        "title": "'"$DOC_TITLE"'",
        "url": "'"$PUBLIC_DOC_URL"'",
        "token": "'"$BODY_TOKEN"'"
      }' -D /tmp/ds_converter.hdr -o /tmp/ds_converter.body || true

    echo "--- /converter status ---"
    status_line /tmp/ds_converter.hdr
    echo "--- /converter body (first 400 bytes) ---"
    head -c 400 /tmp/ds_converter.body; echo
  fi
fi
hr

echo "[7/7] Direct DS test: /ConvertService.ashx (JWT in header)"
if [[ -z "${OO_SECRET}" ]]; then
  echo "Skipped (set OO_SECRET to enable)."
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Skipped (python3 not found)."
  else
    HDR_TOKEN="$(OO_SECRET="$OO_SECRET" SD_URL="$PUBLIC_DOC_URL" DOC_TITLE="$DOC_TITLE" python3 - <<'PY'
import os,time,uuid,json,hmac,hashlib,base64
sec=os.environ["OO_SECRET"]; url=os.environ["SD_URL"]; title=os.environ["DOC_TITLE"]
now=int(time.time())
payload={"payload":{"filetype":"docx","outputtype":"pdf","key":str(uuid.uuid4()),"title":title,"url":url},"iat":now,"exp":now+300}
b64=lambda b: base64.urlsafe_b64encode(b).rstrip(b'=')
hdr=b64(b'{"alg":"HS256","typ":"JWT"}'); pld=b64(json.dumps(payload,separators=(',',':')).encode())
sig=b64(hmac.new(sec.encode(), hdr+b'.'+pld, hashlib.sha256).digest())
print((hdr+b'.'+pld+b'.'+sig).decode())
PY
)"
    [[ -z "$DS_BASE" ]] && DS_BASE="$(url_base "$DOC_JS")"
    [[ -z "$DS_BASE" ]] && DS_BASE="https://onlyoffice.aidocumines.com"

    curl "${CURL_COMMON[@]}" --max-time 300 -X POST "${DS_BASE}/ConvertService.ashx" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $HDR_TOKEN" \
      -d '{
        "async": false,
        "filetype":"docx",
        "outputtype":"pdf",
        "key":"manual-key",
        "title":"'"$DOC_TITLE"'",
        "url":"'"$PUBLIC_DOC_URL"'"
      }' -D /tmp/ds_ashx.hdr -o /tmp/ds_ashx.body || true

    echo "--- /ConvertService.ashx status ---"
    status_line /tmp/ds_ashx.hdr
    echo "--- /ConvertService.ashx body (first 400 bytes) ---"
    head -c 400 /tmp/ds_ashx.body; echo
  fi
fi
hr

echo "Done."

