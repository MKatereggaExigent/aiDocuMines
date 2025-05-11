#!/bin/bash

# Base directory where Nextcloud data is stored on the host
NEXTCLOUD_DATA="/home/aidocumines/Apps/nextcloud/data"

# Base directory where aiDocuMines data is stored
AIDOCUMINES_DATA="/home/aidocumines/Apps/aiDocuMines/media/uploads"

# Nextcloud Admin Credentials
NEXTCLOUD_ADMIN_USER="michael.kateregga@datasqan.com"
NEXTCLOUD_ADMIN_PASS="Micho#25"
NEXTCLOUD_URL="http://aidocumines.com:8080"

# File to store generated passwords
PASSWORD_FILE="nextcloud_user_passwords.txt"
> "$PASSWORD_FILE"  # Clear the file before writing

# Delete all non-admin users from Nextcloud
echo "Deleting all non-admin users from Nextcloud..."
for user in $(docker exec -u www-data nextcloud php occ user:list | awk -F: '{print $1}'); do
    if [ "$user" != "admin" ] && [ "$user" != "$NEXTCLOUD_ADMIN_USER" ]; then
        echo "Deleting Nextcloud user: $user"
        docker exec -u www-data nextcloud php occ user:delete "$user"
        sudo rm -rf "$NEXTCLOUD_DATA/data/$user"
    else
        echo "Skipping admin user: $user"
    fi
done
echo "All non-admin users deleted."

# Loop through each user directory in aiDocuMines
for user_dir in "$AIDOCUMINES_DATA"/*; do
    if [ -d "$user_dir" ]; then
        user_id=$(basename "$user_dir")

        # Define the Nextcloud username and email
        nextcloud_username="user_$user_id"
        user_email="${nextcloud_username}@aidocumines.com"
        nextcloud_user_dir="$NEXTCLOUD_DATA/data/$nextcloud_username/files"

        # Generate a random password for the user
        user_password=$(openssl rand -base64 12)

        echo "Creating Nextcloud user: $nextcloud_username with email: $user_email"
        docker exec -u www-data nextcloud bash -c "export OC_PASS=\"$user_password\" && php occ user:add --password-from-env --display-name=\"$nextcloud_username\" --email=\"$user_email\" \"$nextcloud_username\""

        if [ $? -eq 0 ]; then
            echo "User $nextcloud_username created successfully with email: $user_email and password: $user_password"
            echo "$nextcloud_username:$user_password:$user_email" >> "$PASSWORD_FILE"
        else
            echo "Error: Failed to create user $nextcloud_username."
            continue
        fi

        # Remove admin privileges from the user (if any)
        docker exec -u www-data nextcloud php occ group:remove "$nextcloud_username" admin
        docker exec -u www-data nextcloud php occ user:disable "$nextcloud_username"
        docker exec -u www-data nextcloud php occ user:enable "$nextcloud_username"

        # Create the user's Nextcloud directory
        echo "Creating Nextcloud directory for User ID: $user_id"
        sudo mkdir -p "$nextcloud_user_dir"
        sudo chown -R www-data:www-data "$NEXTCLOUD_DATA/data/$nextcloud_username"
        sudo chmod -R 755 "$NEXTCLOUD_DATA/data/$nextcloud_username"

        # Set permissions on the aiDocuMines data to prevent deletions
        echo "Setting permissions for aiDocuMines data for User ID: $user_id"
        sudo find "$user_dir" -type d -exec chmod 555 {} \;  # Read and execute (no write) for directories
        sudo find "$user_dir" -type f -exec chmod 444 {} \;  # Read-only for files
        sudo chown -R www-data:www-data "$user_dir"

        # Sync the aiDocuMines data to Nextcloud folder
        echo "Syncing data for User ID $user_id..."
        sudo rsync -av --delete "$user_dir/" "$nextcloud_user_dir/"
        sudo chown -R www-data:www-data "$nextcloud_user_dir"

        # Fixing permissions inside the container
        docker exec -u www-data nextcloud bash -c "
            chown -R www-data:www-data /var/www/html/data &&
            chmod -R 755 /var/www/html/data
        "

        # Rescan files to update Nextcloud file index
        echo "Rescanning Nextcloud files for User ID: $user_id"
        docker exec -u www-data nextcloud php occ files:scan "$nextcloud_username"
    fi
done

# Restart Nextcloud Docker container to recognize new files
docker restart nextcloud
echo "Nextcloud containers restarted to recognize new directories."

echo "User passwords saved in: $PASSWORD_FILE"

