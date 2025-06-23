#!/usr/bin/env bash
#
# connect_aidocumines_data_to_nextcloud.sh
#   • Creates/updates one Nextcloud user per aiDocuMines user folder
#   • Rsyncs each user’s uploads into Nextcloud
#   • Stores generated credentials in nextcloud_user_passwords.txt

set -euo pipefail

###############################################################################
# USER CONFIGURATION
###############################################################################
AIDOCUMINES_DATA="/home/aidocumines/Apps/aiDocuMines/media/uploads"
NEXTCLOUD_ADMIN_USER="admin"
NEXTCLOUD_URL="https://nextcloud.aidocumines.com"
PASSWORD_FILE="nextcloud_user_passwords.txt"

###############################################################################
# UTILITY: debug-style colored print (like `icecream`)
###############################################################################
ic() {
  local varname="$1"
  local value="${!varname}"
  echo "🧊  $varname=$value"
}

###############################################################################
# 1. Locate CapRover-managed Nextcloud container
###############################################################################
echo "🔍  Locating CapRover Nextcloud container…"
NC_CONTAINER=$(docker ps \
  --filter "ancestor=nextcloud:latest" \
  --filter "name=srv-captain--nextcloud" \
  --format "{{.Names}}" | head -n 1)

ic NC_CONTAINER
[[ -z "$NC_CONTAINER" ]] && { echo "❌  Nextcloud container not found."; exit 1; }
echo "✅  Using container: $NC_CONTAINER"

###############################################################################
# 2. Detect host path for /var/www/html
###############################################################################
echo -n "📂  Detecting host path of /var/www/html … "
NC_DATA_HOST=$(docker inspect "$NC_CONTAINER" |
  jq -r '.[0].Mounts[] | select(.Destination=="/var/www/html") | .Source')
ic NC_DATA_HOST
[[ -z "$NC_DATA_HOST" ]] && { echo "❌  Could not resolve host path."; exit 1; }
echo "OK"

###############################################################################
# 3. Helper wrappers
###############################################################################
occ()        { docker exec -u www-data "$NC_CONTAINER" php occ "$@"; }
within_nc()  { docker exec -u www-data "$NC_CONTAINER" bash -c "$*"; }

###############################################################################
# 4. Check if Nextcloud is installed
###############################################################################
echo -n "📝  Verifying Nextcloud install… "
occ status | grep -q "installed: true" && echo "OK" || {
  echo "❌  Nextcloud is not installed – aborting."; exit 1; }

###############################################################################
# 5. Delete all users except admin
###############################################################################
echo "🧹  Purging non-admin accounts…"
mapfile -t EXISTING_USERS < <(occ user:list --output=json | jq -r 'keys[]')
ic EXISTING_USERS
for u in "${EXISTING_USERS[@]}"; do
  [[ "$u" == "$NEXTCLOUD_ADMIN_USER" ]] && continue
  occ user:delete "$u" >/dev/null || true
  rm -rf "$NC_DATA_HOST/data/$u"  || true
done
echo "✅  Finished purging."

###############################################################################
# 6. Sync aiDocuMines user folders into Nextcloud
###############################################################################
echo "🔐  New credentials will be written to $PASSWORD_FILE"
: > "$PASSWORD_FILE"

shopt -s nullglob
for SRC_DIR in "$AIDOCUMINES_DATA"/*; do
  [[ -d "$SRC_DIR" ]] || continue
  USER_ID=$(basename "$SRC_DIR")
  NC_USER="user_${USER_ID}"
  NC_EMAIL="${NC_USER}@aidocumines.com"
  NC_FILES="$NC_DATA_HOST/data/$NC_USER/files"

  ic USER_ID
  echo "👤  Syncing $NC_USER …"
  PASS=$(openssl rand -base64 12)

  if occ user:info "$NC_USER" &>/dev/null; then
    echo "   ↺ user exists – resetting password"
    echo "$PASS" | occ user:resetpassword "$NC_USER" --password-from-env
    occ user:setting "$NC_USER" settings email "$NC_EMAIL"
  else
    echo "   ➕ creating"
    within_nc "export OC_PASS='$PASS'; php occ user:add --password-from-env \
               --display-name='$NC_USER' --email='$NC_EMAIL' '$NC_USER'"
  fi

  echo "$NC_USER:$PASS:$NC_EMAIL" >> "$PASSWORD_FILE"

  occ group:remove "$NC_USER" admin || true
  occ user:disable "$NC_USER"      || true
  occ user:enable  "$NC_USER"      || true

  mkdir -p "$NC_FILES"
  chown -R www-data:www-data "$NC_DATA_HOST/data/$NC_USER"
  chmod -R 755               "$NC_DATA_HOST/data/$NC_USER"

  echo "   ↳ syncing $USER_ID → Nextcloud"
  find "$SRC_DIR" -type d -exec chmod 555 {} +   # dirs: r-x
  find "$SRC_DIR" -type f -exec chmod 444 {} +   # files: r--
  chown -R www-data:www-data "$SRC_DIR"

  rsync -a --delete "$SRC_DIR/" "$NC_FILES/"
  chown -R www-data:www-data "$NC_FILES"

  occ files:scan "$NC_USER" >/dev/null
done

###############################################################################
# 7. Permissions and full scan
###############################################################################
echo "🔧  Final permission fix inside container…"
within_nc 'chown -R www-data:www-data /var/www/html/data && chmod -R 755 /var/www/html/data'

echo "🔄  Running occ files:scan --all (quick)…"
occ files:scan --all >/dev/null

echo "🎉  Done.  Credentials saved to $PASSWORD_FILE"

