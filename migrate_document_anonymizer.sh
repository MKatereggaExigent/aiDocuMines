#!/bin/bash

# Name of your web container
CONTAINER_NAME="aidocumines_web"
APP_NAME="document_anonymizer"

echo "🚀 Applying migrations for '$APP_NAME' in container '$CONTAINER_NAME'..."

# Run makemigrations and migrate in a single docker exec
docker exec "$CONTAINER_NAME" bash -c "
  echo '📦 Making migrations for $APP_NAME...';
  python manage.py makemigrations $APP_NAME;
  echo '📂 Applying migrations...';
  python manage.py migrate;
"

echo "✅ Migration process completed."

