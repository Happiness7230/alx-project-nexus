from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
#from accounts.views import RegisterView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import JsonResponse


schema_view = get_schema_view(
    openapi.Info(
        title="Online Poll System API",
        default_version='v1',
        description="API documentation for Online Polling System",
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", lambda request: JsonResponse({"message": "Online Poll API is running"})),
   
    # API routes
    path('api/polls/', include('polls.urls')),
    path('accounts/', include('accounts.urls')),
    #path("api/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Swagger & Redoc
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc-ui'),
    path('schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # Default landing page → redirects to Swagger
    path('', RedirectView.as_view(url='/docs/', permanent=False)),
     path('openapi.json', schema_view.without_ui(cache_timeout=0), name='openapi-json'),
    path('openapi.yaml', schema_view.without_ui(cache_timeout=0), name='openapi-yaml'),
]
