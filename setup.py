from setuptools import setup, find_packages

setup(
    name='django_with_firebase_auth',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Django',
        'djangorestframework',
        'python-decouple',
        'pyrebase4',
        'firebase-admin',
        'django-cors-headers',
        'whitenoise',
        'drf-yasg',
        'celery',
        'redis',
    ],
)
