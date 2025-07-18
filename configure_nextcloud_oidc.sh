#!/bin/bash
set -e

echo "⚙️  Configuring OIDC settings in Nextcloud..."

# Dynamically detect the active Nextcloud container
NEXTCLOUD_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^srv-captain--nextcloud(\.|$)' | head -n 1)

if [[ -z "$NEXTCLOUD_CONTAINER" ]]; then
  echo "❌ Could not find a running Nextcloud container."
  exit 1
fi

# Load credentials
SECRETS_FILE="logs/.superuser_secrets.json"
CLIENT_ID=$(jq -r '.client_id' "$SECRETS_FILE")
CLIENT_SECRET=$(jq -r '.client_secret' "$SECRETS_FILE")
REDIRECT_URI="https://nextcloud.aidocumines.com/index.php/apps/user_oidc/code"

# Enable the OIDC app in Nextcloud
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ app:enable user_oidc || true

# Set OIDC settings
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc client_id --value="$CLIENT_ID"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc client_secret --value="$CLIENT_SECRET"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc provider_url --value="https://aidocumines.aidocumines.com/o"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc redirect_uri --value="$REDIRECT_URI"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc auto_provision --value="1"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc login_button_text --value="Login via aiDocuMines"
docker exec -u www-data "$NEXTCLOUD_CONTAINER" php occ config:app:set user_oidc allow_multiple_user_backends --value="1"

echo "✅ Nextcloud OIDC configuration complete."

