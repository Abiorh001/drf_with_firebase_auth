from celery import Celery
from django.conf import settings
import os


# celery configuration
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drf_with_firebase_auth.settings')
app = Celery('drf_with_firebase_auth')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.broker_connection_retry_on_startup = True