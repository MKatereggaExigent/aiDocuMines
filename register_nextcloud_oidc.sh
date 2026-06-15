#!/bin/bash
set -e

echo "🔐 Registering OIDC client for Nextcloud..."

SECRETS_FILE="logs/.superuser_secrets.json"
REDIRECT_URI="https://nextcloud.apps.datasqan.com/index.php/apps/user_oidc/code"

# Ensure jq is available
if ! command -v jq &>/dev/null; then
  echo "❌ 'jq' is required but not installed."
  exit 1
fi

CLIENT_ID=$(jq -r '.client_id' "$SECRETS_FILE")
CLIENT_SECRET=$(jq -r '.client_secret' "$SECRETS_FILE")
ADMIN_EMAIL=$(jq -r '.admin_email' "$SECRETS_FILE")

# Fetch user ID from CustomUser using email (strip shell noise)
echo "🔍 Resolving user ID for $ADMIN_EMAIL..."
USER_ID=$(python -W ignore manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.get(email='$ADMIN_EMAIL').id)" | tail -n 1)

if ! [[ "$USER_ID" =~ ^[0-9]+$ ]]; then
  echo "❌ Could not resolve a valid numeric user ID. Got: $USER_ID"
  exit 1
fi

echo "👤 Found user ID: $USER_ID"

# Check if app with this client_id already exists
EXISTS=$(python manage.py shell -c "from oauth2_provider.models import Application; print(Application.objects.filter(client_id='$CLIENT_ID').exists())")

if [[ "$EXISTS" == "True" ]]; then
  echo "⚠️  Client ID already exists. Skipping creation."
else
  echo "🚀 Creating new OIDC application for Nextcloud..."
  python manage.py createapplication confidential authorization-code \
    --name "Nextcloud" \
    --client-id "$CLIENT_ID" \
    --client-secret "$CLIENT_SECRET" \
    --redirect-uris "$REDIRECT_URI" \
    --user "$USER_ID"

  echo "✅ OIDC client for Nextcloud registered successfully."
fi

