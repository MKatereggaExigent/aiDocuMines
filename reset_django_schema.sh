#!/bin/bash
set -e  # Exit on any error

# === CONFIGURATION ===
DB_NAME="aidocumines_backend"
DB_USER="aidocu_admin"
DB_PASSWORD="secure1234"
DB_HOST="db"
DB_PORT="5432"
APPS=("core" "file_monitor" "document_ocr" "document_anonymizer" "document_translation" "custom_authentication")

echo "🚨 SAFETY CHECK: Are you sure you're in the project root? Looking for manage.py..."
if [ ! -f "manage.py" ]; then
  echo "❌ ERROR: manage.py not found. Please run this script from your Django project root."
  exit 1
fi

# === STEP 1: Drop and recreate PostgreSQL schema ===
echo "🗑️ Dropping and recreating PostgreSQL schema for DB: $DB_NAME"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" || {
  echo "❌ Failed to reset schema. Check DB connection or credentials."
  exit 1
}

# === STEP 2: Delete old migration files ===
echo "🧹 Deleting old migration files for apps: ${APPS[*]}"
for app in "${APPS[@]}"; do
  if [ -d "$app/migrations" ]; then
    echo "➖ Cleaning $app/migrations..."
    find "$app/migrations" -type f -name "*.py" ! -name "__init__.py" -print -delete
    find "$app/migrations" -type f -name "*.pyc" -print -delete
  else
    echo "⚠️  Skipping $app — no migrations directory found."
  fi
done

# === STEP 3: Recreate migrations ===
echo "🧱 Running makemigrations..."
python manage.py makemigrations "${APPS[@]}" || {
  echo "❌ makemigrations failed."
  exit 1
}

# === STEP 4: Apply migrations ===
echo "📦 Applying all migrations..."
python manage.py migrate || {
  echo "❌ migrate failed."
  exit 1
}

echo "✅ All done! Your schema and migrations are now fully reset and re-applied."

