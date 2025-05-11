#!/bin/bash

# 🚀 Launch Script for Django + Celery + Redis + PostgreSQL

# Configuration
REDIS_HOST="localhost"
REDIS_PORT="6379"
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
CELERY_WORKER_CONCURRENCY=2 # Adjust Celery workers based on your system

echo "🚀 Starting System Services..."

# 1️⃣ **Check if Redis is running**
echo "🔍 Checking Redis status..."
if ! nc -z $REDIS_HOST $REDIS_PORT; then
    echo "❌ Redis is NOT running! Starting Redis..."
    redis-server --daemonize yes
    sleep 2  # Allow Redis to initialize
else
    echo "✅ Redis is already running!"
fi

# 2️⃣ **Wait for PostgreSQL to be Ready**
echo "🔍 Checking PostgreSQL status..."
while ! nc -z $DB_HOST $DB_PORT; do
    echo "⏳ Waiting for database to be ready ($DB_HOST:$DB_PORT)..."
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# 3️⃣ **Stop Existing Celery Instances**
echo "🛑 Stopping any running Celery workers..."
if pkill -f "celery worker"; then
    echo "✅ Celery workers stopped successfully."
else
    echo "⚠️ No Celery workers were running."
fi

# Run makemigrations for the auth 
python manage.py makemigrations auth

python manage.py makemigrations core

python manage.py migrate core

# 🔄 Run auth migrations separately to create the auth_user table first
python manage.py migrate auth

# 🔄 Run all other migrations
python manage.py migrate

# 4️⃣ **Apply Migrations (Ensures DB is up to date)**
echo "🔄 Running Django Migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# 🔹 Superuser Credentials
DJANGO_SUPERUSER_USERNAME="admin"
DJANGO_SUPERUSER_EMAIL="admin@aidocumines.com"
DJANGO_SUPERUSER_PASSWORD="superpassword"

# Create a superuser
# 🔹 Ensure Superuser is Deleted First
echo "🚨 Checking if superuser '$DJANGO_SUPERUSER_USERNAME' exists and deleting it..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').delete()" | python manage.py shell

# 🔹 Create Superuser
echo "👤 Creating new superuser ($DJANGO_SUPERUSER_USERNAME / $DJANGO_SUPERUSER_PASSWORD)..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell

echo "✅ Full database reset, migrations applied, and Django reinstalled successfully!"
echo "✅ Superuser created: Username: $DJANGO_SUPERUSER_USERNAME | Password: $DJANGO_SUPERUSER_PASSWORD"


# 5️⃣ **Collect Static Files (For Production Mode)**
echo "📂 Collecting Static Files..."
python manage.py collectstatic --noinput

# 6️⃣ **Start Celery Worker (Monitored by Watchdog)**
echo "🚀 Starting Celery Worker with Watchdog..."
watchmedo auto-restart --directory=./ --pattern="*.py" --recursive -- \
    celery -A aiDocuMines worker --loglevel=info --concurrency=$CELERY_WORKER_CONCURRENCY &

# 7️⃣ **Start Django Server**
echo "🌍 Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000

# Keep the script running
wait
