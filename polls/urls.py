from django.urls import path, include
from .views import PollCreateListView, PollDetailView, VoteCreateView, PollResultsView
from rest_framework.routers import DefaultRouter
from . import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'polls', views.PollViewSet, basename='poll')

app_name = 'polls'

urlpatterns = [
    path('', PollCreateListView.as_view()),
    path('<int:pk>/', PollDetailView.as_view()),
    path('<int:poll_pk>/vote/', VoteCreateView.as_view()),
    path('<int:poll_pk>/results/', PollResultsView.as_view()),
    path('', include(router.urls)),
]

