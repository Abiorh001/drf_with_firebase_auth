from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view


schema_view = get_schema_view(
    openapi.Info(
        title="User Management API",
        default_version='v1',
        description="API Documentation",
        terms_of_service="",
        contact=openapi.Contact(email=""),
        license=openapi.License(name=""),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

api_version = 'v1'

urlpatterns = [
    path(f'api/{api_version}/admin/', admin.site.urls),
    path(f'api/{api_version}/users/', include('accounts.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path(f'api/{api_version}/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path(f'api/{api_version}/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]