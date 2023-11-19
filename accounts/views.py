from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .models import User
from .serializers import UserSerializer, UserUpdateSerializer, UserEmailUpdateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny, IsAuthenticated
from .firebase_auth.firebase_authentication import FirebaseAuthentication
from .firebase_auth.firebase_authentication import auth as firebase_admin_auth
from .utils.custom_email_verification_link import generate_custom_email_from_firebase
from .utils.custom_password_reset_link import generate_custom_password_link_from_firebase
from django.contrib.auth.hashers import check_password
import re
from drf_with_firebase_auth.settings import auth


class AuthCreateNewUserView(APIView):
    """
    API endpoint to create a new user.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Create a new  user",
        operation_description="Create a new user by providing the required fields.",
        tags=["User Management"],
        request_body=UserSerializer,
        responses={201: UserSerializer(many=False), 400: "User creation failed."}
    )
    def post(self, request, format=None):
        data = request.data
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        included_fields = [email, password, first_name, last_name]
        # Check if any of the required fields are missing
        if not all(included_fields):
            bad_response = {
                "status": "failed",
                "message": "All fields are required."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email is valid
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            bad_response = {
                "status": "failed",
                "message": "Enter a valid email address."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if password is less than 8 characters
        if len(password) < 8:
            bad_response = {
                "status": "failed",
                "message": "Password must be at least 8 characters long."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        # Check if password contains at least one uppercase letter, one lowercase letter, one digit, and one special character
        if password and not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\-]).{8,}$', password):
            bad_response = {
                "status": "failed",
                "message": "Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # create user on firebase
            user = auth.create_user_with_email_and_password(email, password)
            # create user on django database
            uid = user['localId']
            data["firebase_uid"] = uid
            data["is_active"] = True

            # sending custom email verification link
            try:
                user_email = email
                display_name = first_name.capitalize()
                generate_custom_email_from_firebase.delay(user_email, display_name)
            except Exception:
                # delete user from firebase if email verification link could not be sent
                firebase_admin_auth.delete_user(uid)
                bad_response = {
                    "status": "failed",
                    "message": 'Email verification link could not be sent; Please try again.'
                }
                return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
            serializer = UserSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                response = {
                    "status": "success",
                    "message": "User created successfully.",
                    "data": serializer.data
                }
                return Response(response, status=status.HTTP_201_CREATED)
            else:
                auth.delete_user_account(user['idToken'])
                bad_response = {
                    "status": "failed",
                    "message": "User signup failed.",
                    "data": serializer.errors
                }
                return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
           
        except Exception as e:
            bad_response = {
                "status": "failed",
                "message": str(e)
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)


class AuthLoginExisitingUserView(APIView):
    """
    API endpoint to login an existing user.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Login an existing user",
        operation_description="Login an existing user by providing the required fields.",
        tags=["User Management"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the user')
            }
        ),
        responses={200: UserSerializer(many=False), 404: "User does not exist."}
    )
    def post(self, request: Request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email, password)
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "Invalid email or password."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            existing_user = User.objects.get(email=email)
            
            # update password if it is not the same as the one in the database
            if not check_password(password, existing_user.password):
                existing_user.set_password(password)
                existing_user.save()
            
            serializer = UserSerializer(existing_user)
            extra_data = {
                "firebase_id": user['localId'],
                "firebase_access_token": user['idToken'],
                "firebase_refresh_token": user['refreshToken'],
                "firebase_expires_in": user['expiresIn'],
                "firebase_kind": user['kind'],
                "user_data": serializer.data
            }
            response = {
                "status": "success",
                "message": "User logged in successfully.",
                "data": extra_data
            }
            return Response(response, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            auth.delete_user_account(user['idToken'])
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)


class RetrieveUpdateDestroyExistingUser(APIView):
    """
    API endpoint to retrieve, update, or delete an existing user.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    @swagger_auto_schema(
        operation_summary="Retrieve details of an existing user",
        operation_description="Retrieve details of an existing user based on their primary key.",
        tags=["User Management"],
        responses={200: UserSerializer(many=False), 404: "User does not exist."}
    )
    def get(self, request: Request, pk: int):
        try:
            user_firebase_access_token = request.META.get('HTTP_AUTHORIZATION').split(' ').pop()
            decode_access_token = firebase_admin_auth.verify_id_token(user_firebase_access_token)
            user_firebase_uid = decode_access_token.get('uid')
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "Invalid authentication token provided."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=pk, firebase_uid=user_firebase_uid)
        except User.DoesNotExist:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(user)
        response = {
            "status": "success",
            "message": "User retrieved successfully.",
            "data": serializer.data
        }
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update an existing user's information",
        operation_description="Update an existing user's information by providing the fields to be modified.",
        tags=["User Management"],
        request_body=UserUpdateSerializer,
        responses={200: UserUpdateSerializer(many=False), 400: "User update failed.", 404: "User does not exist."}
    )
    def patch(self, request: Request, pk: int):
        data = request.data
        try:
            user_firebase_access_token = request.META.get('HTTP_AUTHORIZATION').split(' ').pop()
            decode_access_token = firebase_admin_auth.verify_id_token(user_firebase_access_token)
            user_firebase_uid = decode_access_token.get('uid')
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "Invalid authentication token provided."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=pk, firebase_uid=user_firebase_uid)
        except User.DoesNotExist:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)

        # Check if any keys in data are not in the list of allowed fields
        invalid_keys = [key for key in data.keys() if key not in ['first_name', 'last_name']]
        if invalid_keys:
            bad_response = {
                            "status": "failed",
                            "message": f"Only 'first_name', 'last_name', can be updated. Invalid field(s): {', '.join(invalid_keys)}"
                        }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        serializer = UserUpdateSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response = {
                "status": "success",
                "message": "User updated successfully.",
                "data": serializer.data
            }
            return Response(response, status=status.HTTP_200_OK)
        else:
            bad_response = {
                "status": "failed",
                "message": "User update failed.",
                "data": serializer.errors
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_summary="Delete an existing user",
        operation_description="Delete an existing user both on firebase and django database  based on their primary key.",
        tags=["User Management"],
        responses={204: "User deleted successfully.", 404: "User does not exist."}
    )
    def delete(self, request: Request, pk):
        try:
            user_firebase_access_token = request.META.get('HTTP_AUTHORIZATION').split(' ').pop()
            decode_access_token = firebase_admin_auth.verify_id_token(user_firebase_access_token)
            user_firebase_uid = decode_access_token.get('uid')
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "Invalid authentication token provided."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=pk, firebase_uid=user_firebase_uid)
            try:
                firebase_admin_auth.delete_user(user_firebase_uid)
            except Exception:
                bad_response = {
                    "status": "failed",
                    "message": "User does not exist on firebase."
                }
                return Response(bad_response, status=status.HTTP_404_NOT_FOUND)
            user.delete()
            response = {
                "status": "success",
                "message": "User deleted successfully."
            }
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)


class UpdateUserEmailAddressView(APIView):
    """
    API endpoint to update an existing  user's email address on firebase and in the database.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    @swagger_auto_schema(
        operation_summary="Update an existing  user's email address on firebase and in the database",
        operation_description="Update an existing user's email address on firebase by providing the new email and firebase uid.",
        tags=["User Management"],
        request_body=UserEmailUpdateSerializer,
        responses={200: "User email updated successfully.", 400: "new email and firebase uid are required.", 404: "User does not exist."}
    )
    def patch(self, request: Request):
        data = request.data
        email = data.get('email')
        firebase_uid = data.get('firebase_uid')
        included_fields = [email, firebase_uid]
        if not all(included_fields):
            bad_response = {
                "status": "failed",
                "message": "new email and firebase uid are required."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            bad_response = {
                "status": "failed",
                "message": "Enter a valid email address."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = firebase_admin_auth.update_user(firebase_uid, email=email)
        except Exception:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)
        try:
            existing_user = User.objects.get(firebase_uid=firebase_uid)
            existing_user.email = email
            existing_user.save()
            response = {
                "status": "success",
                "message": "User email updated successfully.",
            }
            return Response(response, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            auth.delete_user_account(user['idToken'])
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)


class UserPasswordResetView(APIView):
    """
    API endpoint to reset an existing drive user's password.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Reset an existing user's password",
        operation_description="Reset an existing user's password by providing the email address.",
        tags=["User Management"],
        manual_parameters=[
            openapi.Parameter(
                name='email',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Email of the user'
            )
        ],
        responses={200: "Password reset link sent successfully.", 404: "User does not exist."}
        
    )
    def get(self, request: Request):
        
        email = request.query_params.get('email')
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            bad_response = {
                "status": "failed",
                "message": "Enter a valid email address."
            }
            return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            first_name = user.first_name
            # sending custom password reset link
            try:
                user_email = email
                display_name = first_name.capitalize()
                generate_custom_password_link_from_firebase.delay(user_email, display_name)
                response = {
                    "status": "success",
                    "message": "Password reset link sent successfully.",
                }
                return Response(response, status=status.HTTP_200_OK)
            except Exception:
                bad_response = {
                    "status": "failed",
                    "message": "Password reset link could not be sent; Please try again."
                }
                return Response(bad_response, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            bad_response = {
                "status": "failed",
                "message": "User does not exist."
            }
            return Response(bad_response, status=status.HTTP_404_NOT_FOUND)