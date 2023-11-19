from rest_framework.exceptions import APIException
from rest_framework import status


class NoAuthToken(APIException):
    """
    Exception class for no authentication token.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'No authentication token provided.'
    default_code = 'no_auth_token'


class InvalidAuthToken(APIException):
    """
    Exception class for invalid authentication token.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid authentication token provided.'
    default_code = 'invalid_auth_token'


class ExpiredAuthToken(APIException):
    """
    Exception class for expired authentication token.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Expired authentication token provided.'
    default_code = 'expired_auth_token'


class FirebaseError(APIException):
    """
    Exception class for firebase error.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'The user proivded with auth token is not a firebase user. it has no firebase uid.'
    default_code = 'no_firebase_uid'


class EmailVerification(APIException):
    """
    Exception class for email verification.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Email not verified.'
    default_code = 'email_not_verified'