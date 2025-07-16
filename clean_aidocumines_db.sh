#!/bin/bash

# Configuration from .env
DB_CONTAINER="aidocumines_api_layer_db"
DB_NAME="aidocumines_api_layer_database"
DB_USER="aidocumines_administrator"
DB_PORT="5432"
SUPERUSER_EMAIL="admin@aidocumines.com"

echo "🔄 Starting cleanup of database '$DB_NAME'..."

docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<EOF

-- Disable foreign key constraints temporarily
SET session_replication_role = replica;

-- Delete all users except the superuser
DELETE FROM custom_authentication_customuser
WHERE email != '$SUPERUSER_EMAIL';

-- Truncate OAuth2 tokens
TRUNCATE TABLE oauth2_provider_accesstoken RESTART IDENTITY CASCADE;
TRUNCATE TABLE oauth2_provider_refreshtoken RESTART IDENTITY CASCADE;
TRUNCATE TABLE oauth2_provider_grant RESTART IDENTITY CASCADE;

-- Truncate related user profile/permission/group data
TRUNCATE TABLE custom_authentication_userprofile RESTART IDENTITY CASCADE;
TRUNCATE TABLE custom_authentication_user_groups RESTART IDENTITY CASCADE;
TRUNCATE TABLE custom_authentication_user_user_permissions RESTART IDENTITY CASCADE;

-- Clear document-related data
TRUNCATE TABLE core_file RESTART IDENTITY CASCADE;
TRUNCATE TABLE core_metadata RESTART IDENTITY CASCADE;
TRUNCATE TABLE core_run RESTART IDENTITY CASCADE;
TRUNCATE TABLE core_storage RESTART IDENTITY CASCADE;

-- Clear monitoring logs
TRUNCATE TABLE file_monitor_fileeventlog RESTART IDENTITY CASCADE;

-- Clear folder/file operations and versions
TRUNCATE TABLE document_operations_filefolderlink RESTART IDENTITY CASCADE;
TRUNCATE TABLE document_operations_fileversion RESTART IDENTITY CASCADE;
TRUNCATE TABLE document_operations_fileauditlog RESTART IDENTITY CASCADE;
TRUNCATE TABLE document_operations_folder RESTART IDENTITY CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = origin;

EOF

echo "✅ Cleanup complete. Only superuser '$SUPERUSER_EMAIL' retained."

