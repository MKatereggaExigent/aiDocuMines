#!/bin/bash

# Set your container, DB user and DB name
CONTAINER_NAME="aidocumines_api_layer_db"
DB_USER="aidocumines_administrator"
DB_NAME="aidocumines_api_layer_database"

echo "🧹 Cleaning all tables in database: $DB_NAME inside container: $CONTAINER_NAME"

# Compose a TRUNCATE ALL TABLES script dynamically and execute it via docker
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" <<'EOF'
DO $$
DECLARE
    tabname text;
BEGIN
    RAISE NOTICE '📋 Truncating all user tables...';
    FOR tabname IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(tabname) || ' RESTART IDENTITY CASCADE';
        RAISE NOTICE '✅ Truncated: %', tabname;
    END LOOP;
    RAISE NOTICE '✅ All tables truncated successfully.';
END$$;
EOF

