from celery import shared_task
from django.core.mail import send_mail
from django.utils.timezone import now
from .models import CustomUser, PasswordResetToken
from .utils import send_signup_email, send_password_reset_email
from .utils import EMAIL_FROM
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives

@shared_task
def send_signup_email_task(user_id, temporary_password, client_id, client_secret):
    """Celery task to send a signup confirmation email asynchronously."""
    try:
        user = CustomUser.objects.get(id=user_id)
        send_signup_email(user, temporary_password, client_id, client_secret)
        return f"Signup email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} not found"


'''
@shared_task
def send_signup_email_task(user_id, temporary_password):
    """Celery task to send a signup confirmation email asynchronously."""
    try:
        user = CustomUser.objects.get(id=user_id)
        send_signup_email(user, temporary_password)
        return f"Signup email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} not found"
'''

@shared_task
def send_password_reset_email_task(user_id, token_str):
    """Celery task to send a password reset email asynchronously."""
    try:
        user = CustomUser.objects.get(id=user_id)
        reset_token = PasswordResetToken.objects.get(token=token_str)  # ✅ Fix: Query by `token`, not `id`
        send_password_reset_email(user, reset_token)
        return f"Password reset email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User not found (User ID: {user_id})"
    except PasswordResetToken.DoesNotExist:
        return f"Password reset token not found (Token: {token_str})"

@shared_task
def cleanup_expired_tokens():
    """Scheduled Celery task to delete expired password reset tokens."""
    expired_tokens = PasswordResetToken.objects.filter(
        created_at__lt=now() - PasswordResetToken.EXPIRATION_TIME, is_used=False
    )
    count = expired_tokens.count()
    expired_tokens.delete()
    return f"Deleted {count} expired password reset tokens"


@shared_task
def send_admin_password_reset_email_task(user_id, new_password):
    """Send email to notify user that admin reset their password."""
    try:
        user = CustomUser.objects.get(id=user_id)
        subject = "Your aiDocuMines Password Has Been Reset"
        from_email = EMAIL_FROM
        to_email = [user.email]

        context = {
            "user": user,
            "new_password": new_password
        }

        html_content = render_to_string("email/admin_password_reset_email.html", context)
        text_content = (
            f"Dear {user.email},\n\n"
            f"Your password has been reset by an administrator.\n\n"
            f"New Password: {new_password}\n\n"
            f"Please log in and change it as soon as possible.\n\n"
            f"If you did not request this, contact support.\n\n"
            f"Best regards,\n"
            f"aiDocuMines Support Team"
        )

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        return f"Admin password reset email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} not found"


@shared_task
def send_password_reset_success_email_task(user_email):
    """Sends confirmation email after a successful password reset."""
    from django.template.loader import render_to_string
    from django.core.mail import EmailMultiAlternatives
    from .models import CustomUser

    subject = "Your aiDocuMines Password Was Reset"
    from_email = EMAIL_FROM
    to_email = [user_email]

    try:
        user = CustomUser.objects.get(email=user_email)
    except CustomUser.DoesNotExist:
        return f"User with email {user_email} not found"

    # Prepare HTML and plain fallback
    context = {"user": user}
    html_content = render_to_string("email/password_reset_success.html", context)
    text_content = (
        f"Dear {user_email},\n\n"
        f"Your password has been successfully reset.\n"
        f"If you did not initiate this, please contact us immediately at support@aidocumines.com\n\n"
        f"Best regards,\n"
        f"aiDocuMines Support Team"
    )

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
    return f"Password reset confirmation email sent to {user_email}"

