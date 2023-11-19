from django.urls import path
from .views import (
    AuthCreateNewUserView,
    AuthLoginExisitingUserView,
    RetrieveUpdateDestroyExistingUser,
    UpdateUserEmailAddressView,
    UserPasswordResetView
)

urlpatterns = [
    path('auth/sign-up/', AuthCreateNewUserView.as_view(), name='auth-create-user'),
    path('auth/sign-in/', AuthLoginExisitingUserView.as_view(), name='auth-login-drive-user'),
    path('<str:pk>/', RetrieveUpdateDestroyExistingUser.as_view(), name='retrieve-update-user'),
    path('auth/update-email-address/', UpdateUserEmailAddressView.as_view(), name='user-update-email-address'),
    path('auth/reset-password/', UserPasswordResetView.as_view(), name='user-reset-password'),
]
