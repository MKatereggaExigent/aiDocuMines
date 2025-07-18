import os
import requests
import subprocess
from oauthlib.common import generate_token
from django.core.exceptions import ImproperlyConfigured
from .models import IntegrationLog

def generate_nextcloud_autologin_url(user) -> str:
    """
    Ensures the user exists in Nextcloud, sets (or resets) the password, and returns the auto-login URL.
    Additionally, syncs the user's data from aiDocuMines to Nextcloud.
    Logs the integration activity using IntegrationLog.
    """
    if not user.is_active:
        raise Exception("Inactive users cannot be provisioned into Nextcloud.")

    if not user.email:
        raise Exception("Nextcloud provisioning requires a valid email address.")

    # Use a deterministic or random login username (you may switch this later)
    username = f"user_{user.id}"
    email = user.email
    password = generate_token()[:12]  # Temporary password for login

    NEXTCLOUD_ADMIN_USER = os.getenv("NEXTCLOUD_ADMIN_USER", "admin")
    NEXTCLOUD_ADMIN_PASS = os.getenv("NEXTCLOUD_ADMIN_PASS")
    NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL", "https://nextcloud.aidocumines.com")
    AIDOCUMINES_DATA = os.getenv("AIDOCUMINES_DATA", "/home/aidocumines/Apps/aiDocuMines/media/uploads")

    if not NEXTCLOUD_ADMIN_PASS:
        raise ImproperlyConfigured("Missing NEXTCLOUD_ADMIN_PASS in environment.")

    headers = {
        "OCS-APIRequest": "true",
        "Accept": "application/json"
    }

    try:
        # 1. Check if user exists in Nextcloud
        check_url = f"{NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{username}"
        resp = requests.get(check_url, auth=(NEXTCLOUD_ADMIN_USER, NEXTCLOUD_ADMIN_PASS), headers=headers)

        if resp.status_code == 404:
            # 2. Create user if not exists
            create_url = f"{NEXTCLOUD_URL}/ocs/v1.php/cloud/users"
            data = {"userid": username, "password": password, "email": email}
            create_resp = requests.post(create_url, auth=(NEXTCLOUD_ADMIN_USER, NEXTCLOUD_ADMIN_PASS), data=data, headers=headers)

            if create_resp.status_code >= 400:
                IntegrationLog.objects.create(
                    user=user,
                    connector="nextcloud",
                    status="failed",
                    details=f"User creation failed: {create_resp.text}"
                )
                raise Exception(f"Nextcloud user creation failed: {create_resp.text}")
            else:
                IntegrationLog.objects.create(
                    user=user,
                    connector="nextcloud",
                    status="created",
                    details=f"User {username} created in Nextcloud"
                )
        elif resp.status_code == 200:
            # 3. Reset password for existing user
            reset_url = f"{NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{username}/password"
            reset_resp = requests.put(reset_url, auth=(NEXTCLOUD_ADMIN_USER, NEXTCLOUD_ADMIN_PASS),
                                      data={"password": password}, headers=headers)

            if reset_resp.status_code >= 400:
                raise Exception(f"Password reset failed: {reset_resp.text}")

            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="reset",
                details=f"Password reset for existing user {username}"
            )
        else:
            raise Exception(f"Unexpected response checking user: {resp.text}")

        # 4. Synchronize the user's data from aiDocuMines to Nextcloud
        # Using rsync or similar to transfer data without mixing user data
        user_data_path = os.path.join(AIDOCUMINES_DATA, str(user.id))  # Local directory for user data
        nextcloud_user_dir = f"{NEXTCLOUD_URL}/data/{username}/files"  # Nextcloud user folder for their data

        if not os.path.exists(user_data_path):
            raise Exception(f"No data found for user {user.id} at {user_data_path}")

        # Sync data using rsync (may need to customize the command based on your environment)
        sync_command = f"rsync -avz {user_data_path}/ {nextcloud_user_dir}/"
        subprocess.run(sync_command, shell=True, check=True)

        IntegrationLog.objects.create(
            user=user,
            connector="nextcloud",
            status="success",
            details=f"Data synced for user {username} to Nextcloud"
        )

        # 5. Return autologin URL with the correct username and password
        autologin_url = f"https://{username}:{password}@{NEXTCLOUD_URL.replace('https://', '')}"
        return autologin_url

    except Exception as e:
        IntegrationLog.objects.create(
            user=user,
            connector="nextcloud",
            status="error",
            details=str(e)
        )
        raise

