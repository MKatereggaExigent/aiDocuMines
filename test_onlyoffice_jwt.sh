# Save as: test_onlyoffice_jwt.sh
#!/usr/bin/env bash
set -Eeuo pipefail

## ====== Fill these or export before running ======
ACCESS_TOKEN="${ACCESS_TOKEN:-IgILlTIE4QvTyAEhWsIe1ZW8fIIGdy}"
CLIENT_ID="${CLIENT_ID:-aidocumines-angular}"
PROJECT_ID="${PROJECT_ID:-demo}"
SERVICE_ID="${SERVICE_ID:-demo}"
TITLE="${TITLE:-JWT-Diag-$(date +%s).docx}"
FILE_ID="${FILE_ID:-}"   # leave empty to create a new doc

## ====== Endpoints ======
AIDOC_API_LAYER="${AIDOC_API_LAYER:-https://aidocumines-api-layer.aidocumines.com}"
API="$AIDOC_API_LAYER/api/v1/core/onlyoffice"

## ====== Requirements ======
for bin in curl jq python3; do
  command -v "$bin" >/dev/null || { echo "Missing dependency: $bin"; exit 1; }
done

## ====== Helpers ======
curl_json() {
  # Hardened curls to avoid hanging
  curl --fail --show-error --silent \
       --connect-timeout 10 --max-time 30 \
       "$@"
}

urlencode() {
  python3 - <<'PY' "$1"
import sys, urllib.parse as u
print(u.quote(sys.argv[1]))
PY
}

decode_payload_to_file() {
  local token="$1"
  python3 - "$token" > payload.json <<'PY'
import sys, base64, json
t = sys.argv[1]
if '.' not in t:
    print("{}")
    sys.exit(0)
seg = t.split('.')[1]
pad = '=' * (-len(seg) % 4)
payload = json.loads(base64.urlsafe_b64decode(seg + pad).decode('utf-8', 'ignore'))
# unwrap .payload if present, drop iat/exp
if isinstance(payload, dict) and 'payload' in payload and isinstance(payload['payload'], dict):
    payload = payload['payload']
payload.pop('iat', None); payload.pop('exp', None)
print(json.dumps(payload, indent=2))
PY
}

## ====== 1) Create doc (optional) ======
if [[ -z "$FILE_ID" ]]; then
  echo "1) Creating DOCX…"
  enc_title="$(urlencode "$TITLE")"
  create_json="$(
    curl_json -X POST \
      "$API/create-docx/?project_id=$PROJECT_ID&service_id=$SERVICE_ID&title=$enc_title" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "X-Client-ID: $CLIENT_ID" \
      -H "Accept: application/json"
  )"
  FILE_ID="$(jq -r '.file_id' <<<"$create_json")"
  [[ "$FILE_ID" =~ ^[0-9]+$ ]] || { echo "Failed to create doc: $create_json"; exit 2; }
  echo "   file_id=$FILE_ID"
else
  echo "1) Using existing file_id=$FILE_ID"
fi

## ====== 2) Fetch editor config ======
echo "2) Fetching editor config…"
cfg_json="$(curl_json "$API/editor-config/?file_id=$FILE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Accept: application/json")"
printf '%s\n' "$cfg_json" > cfg.json

docjs="$(jq -r '.docServerApiJs' cfg.json)"
apijs_status="$(curl --silent --head --connect-timeout 10 --max-time 15 "$docjs" | sed -n '1p')"
echo "   api.js => $apijs_status"

token="$(jq -r '.config.token' cfg.json)"
if [[ -z "$token" || "$token" == "null" ]]; then
  echo "FAIL: config.token is missing"; exit 3
fi

## ====== 3) Decode JWT payload ======
echo "3) Decoding JWT…"
decode_payload_to_file "$token"
jq '.config | del(.token)' cfg.json > conf.json

## ====== 4) Compare structures ======
echo "4) Comparing token payload vs. config…"
if diff -u conf.json payload.json >/dev/null; then
  echo "PASS ✅  Token payload matches the editor config."
  exit 0
else
  echo "FAIL ❌  Token payload does not match the editor config."
  echo "---- config (server) ----"; jq . conf.json
  echo "---- token payload ----"; jq . payload.json
  echo "Hint: If payload shows a top-level \"payload\" wrapper, sign the config itself (no wrapper)."
  exit 4
fi

