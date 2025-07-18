# integrations/tasks.py

from celery import shared_task
from django.contrib.auth import get_user_model
from integrations.utils import generate_nextcloud_autologin_url
from integrations.models import IntegrationLog


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_nextcloud_url_async(self, user_id):
    """
    Celery task to generate autologin URL for Nextcloud for a given user.
    This includes user creation, password reset, and syncing user data to Nextcloud.
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        
        # Generate the autologin URL using the updated logic from utils.py
        url = generate_nextcloud_autologin_url(user)

        # Log success in IntegrationLog (if not already handled in utils)
        IntegrationLog.objects.create(
            user=user,
            connector="nextcloud",
            status="autologin_ready",
            details=f"Autologin URL generated successfully for user {user.id}"
        )
        return url

    except User.DoesNotExist:
        # If the user doesn't exist, log it and raise an exception
        IntegrationLog.objects.create(
            user=None,
            connector="nextcloud",
            status="error",
            details=f"User with ID {user_id} does not exist"
        )
        raise

    except Exception as e:
        # Log failure in IntegrationLog if an error occurs during the task
        try:
            IntegrationLog.objects.create(
                user_id=user_id,
                connector="nextcloud",
                status="error",
                details=f"Autologin task failed: {str(e)}"
            )
        except Exception:
            pass  # If logging fails, don't mask the original error

        # Retry the task
        raise self.retry(exc=e)

