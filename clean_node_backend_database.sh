#!/usr/bin/env bash

# Define variables
CONTAINER="aidocumines_backend_db"
DB_USER="aidocu_backend_user"
DB_NAME="aidocumines_backend"
APP_CONTAINER="aidocumines_web"  # the container that has manage.py

echo "⚙️ Dropping all tables in $DB_NAME..."

docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<'EOF'
DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
EOF

echo "🧹 Dropping all views in $DB_NAME..."

docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<'EOF'
DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
    ) LOOP
        EXECUTE 'DROP VIEW IF EXISTS public.' || quote_ident(r.table_name) || ' CASCADE';
    END LOOP;
END $$;
EOF

echo "🚀 Running Django migrations..."

docker exec -i "$APP_CONTAINER" bash -c "cd /app && python manage.py migrate"

echo "✅ Done. Database has been reset and re-initialized."

