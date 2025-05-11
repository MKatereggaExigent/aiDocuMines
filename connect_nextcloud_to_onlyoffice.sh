#!/bin/bash

# Base directory where Nextcloud data is stored on the host
NEXTCLOUD_DATA="/home/aidocumines/Apps/nextcloud/data"

# Nextcloud Admin Credentials
NEXTCLOUD_ADMIN_USER="michael.kateregga@datasqan.com"
NEXTCLOUD_ADMIN_PASS="Micho#25"
NEXTCLOUD_URL="http://aidocumines.com:8080"

# ONLYOFFICE Server Configuration
ONLYOFFICE_URL="http://aidocumines.com:85"  # ONLYOFFICE server URL

# Get the list of existing Nextcloud users
existing_users=$(docker exec -u www-data nextcloud php occ user:list | awk -F: '{print $1}' | tr -d ' ' | sed 's/^-//')

# Loop through each Nextcloud user to configure ONLYOFFICE
for user in $existing_users; do
    if [ "$user" != "admin" ] && [ "$user" != "$NEXTCLOUD_ADMIN_USER" ]; then
        echo "Configuring ONLYOFFICE for Nextcloud user: $user"

        # Create the Connection URL for the user
        connection_url="${NEXTCLOUD_URL}/remote.php/dav/files/${user}/"

        # Set the email format (same as we did in user creation)
        user_email="${user}@aidocumines.com"

        # Generate a password for ONLYOFFICE
        password=$(openssl rand -base64 12)

        # Set ONLYOFFICE configurations for the user
        docker exec -u www-data nextcloud php occ config:app:set onlyoffice DocumentServerUrl --value="$ONLYOFFICE_URL/"
        docker exec -u www-data nextcloud php occ config:app:set onlyoffice DocumentServerInternalUrl --value="$ONLYOFFICE_URL/"
        docker exec -u www-data nextcloud php occ config:app:set onlyoffice StorageUrl --value="$connection_url"

        # Create the user in ONLYOFFICE using the API with admin credentials
        response=$(curl -s -X POST "${ONLYOFFICE_URL}/api/2.0/people" \
            -H "Content-Type: application/json" \
            -H "Authorization: Basic $(echo -n "${NEXTCLOUD_ADMIN_USER}:${NEXTCLOUD_ADMIN_PASS}" | base64)" \
            -d '{
                "email": "'"$user_email"'",
                "password": "'"$password"'",
                "firstname": "'"$user"'",
                "lastname": "User",
                "admin": false
            }')

        # Check if the user creation was successful
        if echo "$response" | grep -q '"statusCode":201'; then
            echo "ONLYOFFICE configured for user: $user"
            echo "User: $user"
            echo "Email: $user_email"
            echo "Login URL: $ONLYOFFICE_URL/Auth.aspx"
            echo "Login: $user_email"
            echo "Password: $password"
            echo "===================================="
        else
            echo "Error creating ONLYOFFICE user: $user"
            echo "Response: $response"
        fi
    fi
done

# Restart Nextcloud Docker container to apply changes
docker restart nextcloud
echo "Nextcloud containers restarted to recognize ONLYOFFICE integration."

echo "ONLYOFFICE configuration completed for all users!"

