#!/bin/bash

set -e  # Exit immediately if a command fails
set -o pipefail  # Catch errors in pipelines

# Configuration
REDIS_HOST="localhost"
REDIS_PORT="6379"
DB_HOST="localhost"
DB_PORT="5432"
CELERY_WORKER_CONCURRENCY=2
DJANGO_SUPERUSER_USERNAME="admin"
DJANGO_SUPERUSER_EMAIL="admin@aidocumines.com"
DJANGO_SUPERUSER_PASSWORD="superpassword"
DB_NAME="aidocuminesdb"
DB_USER="michaelkateregga"
VENV_PATH="vmEnv/bin/activate"

# Remove all the old migrations
echo "🗑️ Removing old migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

echo "🛑 Stopping all relevant services..."
# Stop any running services
pkill -9 -f "celery worker" || echo "⚠️ No Celery workers running."
pkill -9 -f "python manage.py runserver" || echo "⚠️ No Django server running."
lsof -t -i:8000 | xargs kill -9 || echo "⚠️ No process running on port 8000."
redis-cli shutdown || echo "⚠️ Redis was not running."

# 1️⃣ **Ensure Virtual Environment is Activated**
echo "🟢 Activating Virtual Environment..."
source $VENV_PATH || { echo "❌ ERROR: Virtual environment not found! Exiting..."; exit 1; }

# 2️⃣ **Ensure Redis is Running**
echo "🔍 Checking Redis status..."
if ! nc -z $REDIS_HOST $REDIS_PORT; then
    echo "❌ Redis is NOT running! Starting Redis..."
    redis-server --daemonize yes
    sleep 2  # Allow Redis to initialize
else
    echo "✅ Redis is already running!"
fi

# 3️⃣ **Ensure PostgreSQL is Running**
echo "🔍 Checking PostgreSQL status..."
until nc -z $DB_HOST $DB_PORT; do
    echo "⏳ Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# 4️⃣ **Ensure PostgreSQL User Exists**
echo "🔍 Checking if PostgreSQL user '$DB_USER' exists..."
USER_EXISTS=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'")
if [[ "$USER_EXISTS" != "1" ]]; then
  echo "❌ ERROR: PostgreSQL user '$DB_USER' does not exist! Please create it first."
  exit 1
fi

# 5️⃣ **Drop & Recreate Database**
# echo "🔥 Resetting database: $DB_NAME..."
# psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "DROP DATABASE IF EXISTS $DB_NAME;"
# psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# 5️⃣ **Force Disconnect Active Sessions & Drop Database**
echo "🔥 Terminating active sessions on database: $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();
"

echo "🔥 Dropping database: $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "🛠️ Creating new database: $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"


# 6️⃣ **Remove Old Migrations & Media Files**
echo "🗑️ Removing old migration files and media..."
find . -path "*/migrations/*.py" ! -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
rm -rf media/*

# 7️⃣ **Ensure Dependencies are Installed (Reinstall Django if Needed)**
echo "📦 Checking and installing dependencies..."
pip install --upgrade -r production_requirements.txt
pip install --force-reinstall django  # Force reinstall Django to prevent corruption

# 8️⃣ **Pause to Prevent Race Conditions**
echo "⏳ Waiting for dependencies to stabilize..."
sleep 5

# 9️⃣ **Ensure Django is Accessible**
if ! python -c "import django" &> /dev/null; then
    echo "❌ ERROR: Django is still not installed! Exiting..."
    exit 1
fi
echo "✅ Django is installed and working!"

# 🔟 **Apply Migrations**
echo "🔄 Running Django Migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --run-syncdb

# 1️⃣1️⃣ **Ensure Superuser Exists & Store OAuth2 Credentials**
echo "👤 Ensuring superuser exists and storing credentials..."
python manage.py shell <<EOF
import json
import os
from django.contrib.auth import get_user_model
from oauth2_provider.models import Application

User = get_user_model()
superuser_file = "aiDocuMines/.superuser_secrets.json"

# ✅ Check if the superuser exists
if not User.objects.filter(email="$DJANGO_SUPERUSER_EMAIL").exists():
    print("👤 Creating new superuser ($DJANGO_SUPERUSER_USERNAME)")

    user = User.objects.create_superuser(
        email="$DJANGO_SUPERUSER_EMAIL",
        password="$DJANGO_SUPERUSER_PASSWORD",
        organisation="AI DocuMines",
        contact_name="Admin User",
        contact_phone="+27 000 000 000",
        address="Admin Address",
        industry="AI Research",
        use_case="System setup"
    )

    # ✅ Step 1: Create Application object **without saving yet**
    app = Application(
        user=user,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        name="System Admin API Access",
    )

    # ✅ Step 2: Extract **raw** client_secret BEFORE saving (prevents hashing)
    raw_client_secret = app.client_secret  # ✅ This is the valid OAuth2 secret

    # ✅ Step 3: Now save the application (this will hash the secret in DB)
    app.save()

    # ✅ Step 4: Store credentials securely
    secrets_data = {
        "admin_email": "$DJANGO_SUPERUSER_EMAIL",
        "admin_password": "$DJANGO_SUPERUSER_PASSWORD",
        "client_id": app.client_id,
        "client_secret": raw_client_secret  # ✅ Saving the un-hashed secret here
    }

    with open(superuser_file, "w") as f:
        json.dump(secrets_data, f, indent=4)

    print("✅ Superuser and OAuth2 credentials saved successfully in aiDocuMines/.superuser_secrets.json!")

else:
    print("⚠️ Superuser already exists.")

    # ✅ If secrets file is missing, regenerate OAuth credentials
    if not os.path.exists(superuser_file):
        print("🔍 Superuser secrets file missing. Regenerating...")
        user = User.objects.filter(email="$DJANGO_SUPERUSER_EMAIL").first()

        # ✅ Step 1: Create a new application **without saving yet**
        app = Application(
            user=user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            name="System Admin API Access",
        )

        # ✅ Step 2: Extract **raw** client_secret BEFORE saving
        raw_client_secret = app.client_secret  # ✅ This is the valid OAuth2 secret

        # ✅ Step 3: Now save the application
        app.save()

        secrets_data = {
            "admin_email": user.email,
            "client_id": app.client_id,
            "client_secret": raw_client_secret
        }

        with open(superuser_file, "w") as f:
            json.dump(secrets_data, f, indent=4)

        print("✅ Superuser credentials re-saved successfully in aiDocuMines/.superuser_secrets.json!")
EOF

# 1️⃣2️⃣ **Collect Static Files**
echo "📂 Collecting Static Files..."
python manage.py collectstatic --noinput

# 1️⃣3️⃣ **Start Django Server First**
echo "🌍 Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000 &  # Run in the background

# Update pip
echo "📦 Updating pip..."
pip install --upgrade pip

# 1️⃣4️⃣ **Wait for Django to be Ready Before Starting Celery**
echo "⏳ Waiting for Django to fully initialize..."
sleep 10  # Allow Django to fully initialize

# 1️⃣5️⃣ **Ensure Celery Registers Tasks Properly**
echo "🛑 Stopping Celery Workers..."
pkill -9 -f "celery worker" || echo "⚠️ No Celery workers running."

# Ensure Celery is properly registered
echo "🔍 Checking if Celery Recognizes Tasks..."
python manage.py shell <<EOF
from celery import current_app
print("Registered Celery Tasks:")
print(current_app.tasks.keys())
EOF

# 1️⃣6️⃣ **Start Celery Worker AFTER Django is Running**
echo "🚀 Starting Celery Worker..."
celery -A aiDocuMines worker --loglevel=info --concurrency=$CELERY_WORKER_CONCURRENCY
