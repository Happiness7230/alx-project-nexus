from rest_framework import generics, views, status, permissions, viewsets
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from .models import Poll, Option, Vote
from .serializers import PollSerializer, VoteSerializer
from django.core.cache import cache


class PollCreateListView(generics.ListCreateAPIView):
    """List all polls or create a new poll."""
    queryset = Poll.objects.prefetch_related('options').all()
    serializer_class = PollSerializer


class PollDetailView(generics.RetrieveAPIView):
    """Retrieve a single poll with its options."""
    queryset = Poll.objects.prefetch_related('options')
    serializer_class = PollSerializer


class VoteCreateView(views.APIView):
    """Handle voting on polls with duplicate protection."""
    permission_classes = (permissions.AllowAny,)  # Changed from IsAuthenticated to AllowAny

    def post(self, request, poll_pk):
        """
        Create a vote for a poll option.
        
        Expected POST data:
        - option_id: ID of the option to vote for
        - voter_uuid: (optional) Unique identifier for anonymous voters
        """
        # Fetch poll
        poll = get_object_or_404(Poll, pk=poll_pk)
        
        # Check if poll is active and not expired
        if poll.is_expired() or not poll.is_active:
            return Response(
                {"detail": "Poll is closed."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get option from request data
        option_id = request.data.get('option_id') or request.data.get('option')
        if not option_id:
            return Response(
                {"detail": "Option id required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        option = get_object_or_404(Option, pk=option_id, poll=poll)
        
        # Determine voter identity
        user = request.user if request.user.is_authenticated else None
        voter_uuid = request.data.get('voter_uuid')
        voter_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        
        # Duplicate protection
        existing = Vote.objects.filter(poll=poll)
        
        if user and existing.filter(user=user).exists():
            return Response(
                {"detail": "User has already voted."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        elif voter_uuid and existing.filter(voter_uuid=voter_uuid).exists():
            return Response(
                {"detail": "Voter has already voted."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        elif voter_ip and existing.filter(voter_ip=voter_ip).exists():
            return Response(
                {"detail": "IP has already voted."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create vote atomically
        with transaction.atomic():
            vote = Vote.objects.create(
                poll=poll,
                option=option,
                user=user,
                voter_uuid=voter_uuid,
                voter_ip=voter_ip
            )
            Option.objects.filter(pk=option.pk).update(vote_count=F('vote_count') + 1)
            
            # Invalidate cache
            cache_key = f"poll_results:{poll.pk}"
            cache.delete(cache_key)
            
        return Response(
            VoteSerializer(vote).data, 
            status=status.HTTP_201_CREATED
        )


class PollResultsView(views.APIView):
    """
    Returns vote counts per option with caching.
    Efficiently uses aggregation and denormalized vote_count field.
    """
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request, poll_pk):
        """Get poll results with caching."""
        cache_key = f"poll_results:{poll_pk}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        poll = get_object_or_404(Poll, pk=poll_pk)
        
        # Use denormalized vote_count for efficiency
        options = list(poll.options.all().values('id', 'text', 'vote_count'))
        payload = {
            "poll_id": poll.pk, 
            "title": poll.title, 
            "results": options
        }

        # Cache for short duration (5 seconds)
        cache.set(cache_key, payload, timeout=5)
        return Response(payload)


class PollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Poll CRUD operations.
    Provides list, create, retrieve, update, and delete actions.
    """
    queryset = Poll.objects.prefetch_related('options').all()
    serializer_class = PollSerializer
    permission_classes = (permissions.AllowAny,)
