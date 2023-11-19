from accounts.firebase_auth.firebase_authentication import auth as firebase_admin_auth
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger


# celery logger
logger = get_task_logger(__name__)


# create custom email verification link using celery background task
@shared_task()
def generate_custom_email_from_firebase(user_email, display_name):
    action_code_settings = firebase_admin_auth.ActionCodeSettings(
        url='https://www.yourwebsite.example/',
        handle_code_in_app=True,
    )
    custom_verification_link = firebase_admin_auth.generate_email_verification_link(user_email, action_code_settings)
    subject = 'Verify your email address'
    message = f'Hello {display_name},\n\nPlease verify your email address by clicking on the link below:\n\n{custom_verification_link}\n\nThanks,\nYour website team'
    send_email(subject, message, user_email)


# send email using django send_mail
def send_email(subject, message, user_email):
    from_email = settings.EMAIL_HOST_USER
    recipient = user_email
    send_mail(subject, message, from_email, [recipient], fail_silently=False)