#!/usr/bin/env bash
set -e

echo "🚀 Updating aidocumines_api_layer_database and user inside PostgreSQL..."

# Database and user variables
DB_NAME="aidocumines_api_layer_database"
DB_USER="aidocumines_administrator"
DB_PASSWORD="SeCUREPassL0L6"
DB_HOST="db"
DB_PORT="5432"

# Postgres superuser (inside container)
POSTGRES_SUPERUSER="postgres"

# Run inside the network with the postgres container
docker run --rm \
  --network captain-overlay-network \
  -e PGPASSWORD=$POSTGRES_SUPERUSER \
  postgres:15 \
  bash -c "
    echo '🧹 Dropping existing connections to $DB_NAME...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';
    \"

    echo '🗑️ Dropping database $DB_NAME if exists...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      DROP DATABASE IF EXISTS $DB_NAME;
    \"

    echo '🗑️ Dropping user $DB_USER if exists...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      DROP ROLE IF EXISTS $DB_USER;
    \"

    echo '👤 Creating user $DB_USER with password...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    \"

    echo '🛠️ Creating database $DB_NAME owned by $DB_USER...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      CREATE DATABASE $DB_NAME OWNER $DB_USER;
    \"

    echo '🔐 Granting all privileges on $DB_NAME to $DB_USER...'
    psql -h $DB_HOST -U $POSTGRES_SUPERUSER -p $DB_PORT -d postgres -c \"
      GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    \"
  "

echo "✅ Database and user setup complete!"

