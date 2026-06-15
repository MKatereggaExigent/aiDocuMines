#!/bin/bash

# 🔹 Set PostgreSQL Database Credentials
DB_NAME="aidocuminesdb"
DB_USER="michaelkateregga"  # <-- Change to your PostgreSQL username
DB_PASSWORD="securepassword"
DB_HOST="localhost"
DB_PORT="5432"

# 🔹 Superuser Credentials
DJANGO_SUPERUSER_USERNAME="admin"
DJANGO_SUPERUSER_EMAIL="michael.kateregga@datasqan.com"
DJANGO_SUPERUSER_PASSWORD="superpassword"


# 🔹 Stop Celery Workers
pkill -9 -f celery

echo "🚀 Starting FULL database and project reset..."

# 🔹 Check if PostgreSQL user exists
echo "🔍 Checking if PostgreSQL role '$DB_USER' exists..."
if ! psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  echo "❌ ERROR: PostgreSQL role '$DB_USER' does not exist! Please create it first."
  exit 1
fi

# 🔹 Drop & Recreate the Database
echo "🔥 Dropping and recreating database: $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# 🔹 Delete all migration files (except __init__.py)
echo "🗑️  Deleting all migration files..."
find . -path "*/migrations/*.py" ! -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# 🔹 Remove media/uploads directory (Uploaded files)
echo "🗑️  Deleting media files..."
rm -rf media/*

# 🔹 Reinstall Python dependencies
echo "📦 Reinstalling Python dependencies..."
pip install -r requirements.txt

# 🔹 Uninstall & Reinstall Django
echo "🔥 Reinstalling Django..."
pip uninstall -y django
pip install django
pip install --upgrade pip

# 🔹 Run fresh migrations
echo "🔄 Running makemigrations..."
python manage.py makemigrations auth  # Ensure auth_user table is created first
python manage.py makemigrations

echo "📌 Running migrate..."
python manage.py migrate --run-syncdb  # Ensures all tables exist

# Install en-encore-web-lg if it's not already installed using python -m spacy download en_core_web_lg
# python -m spacy download en_core_web_lg

# 🔹 Ensure Superuser is Deleted First
echo "🚨 Checking if superuser '$DJANGO_SUPERUSER_USERNAME' exists and deleting it..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').delete()" | python manage.py shell

# 🔹 Create Superuser
echo "👤 Creating new superuser ($DJANGO_SUPERUSER_USERNAME / $DJANGO_SUPERUSER_PASSWORD)..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell

echo "✅ Full database reset, migrations applied, and Django reinstalled successfully!"
echo "✅ Superuser created: Username: $DJANGO_SUPERUSER_USERNAME | Password: $DJANGO_SUPERUSER_PASSWORD"
