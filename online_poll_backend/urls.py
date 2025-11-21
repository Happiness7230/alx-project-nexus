"""
URL configuration for online_poll_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core.swagger import swagger_urls
from django.urls import path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from accounts.views import RegisterView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("", lambda request: JsonResponse({"message": "Online Poll API is running"})),
    path('admin/', admin.site.urls),
    path('api/polls/', include('polls.urls')),
    path("api/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
] + swagger_urls

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="Online Poll System API",
        default_version='v1',
        description="""
        # Online Poll System API Documentation
        
        A comprehensive RESTful API for creating and managing online polls with real-time voting.
        
        ## Features
        
        * **Poll Management**: Create, update, and delete polls
        * **Voting System**: Cast votes with duplicate prevention
        * **Real-time Results**: Get live vote counts and percentages
        * **Expiry Support**: Set poll expiration dates
        * **Vote Validation**: Prevent duplicate voting per user
        
        ## Common Use Cases
        
        ### 1. Create a Poll
        ```json
        POST /api/polls/
        {
          "title": "Favorite Programming Language",
          "description": "Vote for your favorite language",
          "expires_at": "2025-12-31T23:59:59Z",
          "options": [
            {"text": "Python", "order": 1},
            {"text": "JavaScript", "order": 2},
            {"text": "Java", "order": 3}
          ]
        }
        ```
        
        ### 2. Cast a Vote
        ```json
        POST /api/polls/{poll_id}/vote/
        {
          "option_id": 1,
          "voter_identifier": "user@example.com"
        }
        ```
        
        ### 3. Get Results
        ```
        GET /api/polls/{poll_id}/results/
        ```
        """,
        contact=openapi.Contact(email="support@pollsystem.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('polls.urls')),
    
    # Swagger documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
