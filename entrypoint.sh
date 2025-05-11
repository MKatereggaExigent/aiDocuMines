#!/bin/bash

set -e  # Stop script on any error

echo "🚀 Starting System Services..."

# ✅ **Properly Load Environment Variables (Ignoring Comments and Empty Lines)**
if [ -f "/app/.env" ]; then
    echo "✅ Loading environment variables from .env"
    set -o allexport
    while IFS='=' read -r key value; do
        # Ignore comments and empty lines
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue

        # Trim spaces and remove surrounding quotes
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs | sed -E 's/^"(.*)"$/\1/')

        export "$key"="$value"
    done < /app/.env
    set +o allexport
else
    echo "⚠️ Warning: .env file not found. Proceeding with defaults."
fi

# ✅ **Ensure Required Environment Variables Are Set**
required_vars=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "POSTGRES_HOST" "CONNECTION_STRING")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ ERROR: Missing required environment variable: $var"
        exit 1
    fi
done

# ✅ **Wait for PostgreSQL to be Ready**
echo "🔍 Checking PostgreSQL status..."
until PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
    echo "⏳ Waiting for PostgreSQL to be ready ($POSTGRES_HOST:$POSTGRES_PORT)..."
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# ✅ **Run Migrations (Only for db_prepare)**
if [ "$SERVICE_NAME" = "db_prepare" ]; then
    echo "🔄 Running Django Migrations..."
    python manage.py migrate --noinput

# ✅ **Create Superuser & OAuth2 Credentials If Not Exists**
echo "🚨 Checking if superuser '$DJANGO_SUPERUSER_USERNAME' exists..."
python manage.py shell <<EOF
import json
import os
from django.contrib.auth import get_user_model
from custom_authentication.models import Client
from oauth2_provider.models import Application
from oauth2_provider.generators import generate_client_secret

User = get_user_model()
superuser_file = "/app/logs/.superuser_secrets.json"

# Create or retrieve the client (tenant) instance
client, _ = Client.objects.get_or_create(
    name="AI DocuMines",
    defaults={
        "address": "Admin Address",
        "industry": "AI Research",
        "use_case": "System setup"
    }
)

if not User.objects.filter(email="$DJANGO_SUPERUSER_EMAIL").exists():
    print("👤 Creating new superuser: $DJANGO_SUPERUSER_USERNAME")
    user = User.objects.create_superuser(
        email="$DJANGO_SUPERUSER_EMAIL",
        password="$DJANGO_SUPERUSER_PASSWORD",
        client=client,
        contact_name="Admin User",
        contact_phone="+27 000 000 000",
        address="Admin Address",
        industry="AI Research",
        use_case="System setup"
    )

    # ✅ Generate and store OAuth2 credentials
    raw_client_secret = generate_client_secret()
    app = Application.objects.create(
        user=user,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_PASSWORD,
        name="System Admin API Access",
        client_secret=raw_client_secret
    )

    secrets_data = {
        "admin_email": "$DJANGO_SUPERUSER_EMAIL",
        "admin_password": "$DJANGO_SUPERUSER_PASSWORD",
        "client_id": app.client_id,
        "client_secret": raw_client_secret
    }

    with open(superuser_file, "w") as f:
        json.dump(secrets_data, f, indent=4)

    print("✅ Superuser and OAuth2 credentials saved successfully!")
else:
    print("✅ Superuser already exists!")
EOF

    touch /app/logs/migrations_complete
fi

# ✅ **Collect Static Files (Only for web)**
if [ "$SERVICE_NAME" = "web" ]; then
    echo "📂 Collecting Static Files..."
    python manage.py collectstatic --noinput
fi

# ✅ **Start Celery Services**
if [ "$SERVICE_NAME" = "celery" ]; then
    echo "🕒 Waiting 10s to ensure Django is ready..."
    sleep 10
    echo "🚀 Starting Celery Worker..."
    exec celery -A aiDocuMines worker --loglevel=info --concurrency=4
elif [ "$SERVICE_NAME" = "celery_beat" ]; then
    echo "🕒 Waiting 10s to ensure Celery Worker is ready..."
    sleep 10
    echo "🚀 Starting Celery Beat..."
    exec celery -A aiDocuMines beat --loglevel=info
fi

# ✅ **Start Django Application (Only for web)**
if [ "$SERVICE_NAME" = "web" ]; then
    echo "🌍 Starting Gunicorn Server..."
    # exec gunicorn aiDocuMines.wsgi:application --bind 0.0.0.0:8020 --timeout 120 --log-level debug
    exec gunicorn aiDocuMines.wsgi:application --bind 0.0.0.0:8020 --timeout 120 --log-level debug
fi

# ✅ Start Supervisor for File Monitoring
if [ "$SERVICE_NAME" = "file_monitor" ]; then
    echo "👁️  Starting Supervisor for File Monitoring..."
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi


# ✅ Pull default Ollama models (Only for ollama)
if [ "$SERVICE_NAME" = "ollama" ]; then
    echo "📦 Pulling default Ollama models: mistral, llama3, deepseek-coder..."
    ollama pull mistral || echo "⚠️ Failed to pull 'mistral'"
    ollama pull llama3 || echo "⚠️ Failed to pull 'llama3'"
    ollama pull deepseek-coder:6.7b || echo "⚠️ Failed to pull 'deepseek-coder:6.7b'"
    echo "✅ Ollama models ready."
    exit 0  # Prevent further execution for ollama container
fi



python manage.py collectstatic --noinput
