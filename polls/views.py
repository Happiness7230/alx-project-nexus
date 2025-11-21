from rest_framework import generics, views, viewsets, status, permissions
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from .models import Poll, Option, Vote
from .serializers import PollSerializer, VoteSerializer
from django.core.cache import cache
from django.db.models import F

class PollViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing poll instances.
    """
    queryset = Poll.objects.all().order_by('-created_at')
    serializer_class = PollSerializer

class PollCreateListView(generics.ListCreateAPIView):
    queryset = Poll.objects.prefetch_related('options').all()
    serializer_class = PollSerializer

class PollDetailView(generics.RetrieveAPIView):
    queryset = Poll.objects.prefetch_related('options')
    serializer_class = PollSerializer

class VoteCreateView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, poll_pk, poll_id, option_pk=None):
        # fetch poll
        poll = get_object_or_404(Poll,id=poll_id, pk=poll_pk)
        if poll.is_expired() or not poll.is_active:
            return Response({"detail": "Poll is closed."}, status=status.HTTP_400_BAD_REQUEST)

        # get option from request or URL
        option_id = option_pk or request.data.get('option')
        if not option_id:
            return Response({"detail": "Option id required."}, status=status.HTTP_400_BAD_REQUEST)

        option = get_object_or_404(Option, pk=option_id, poll=poll)

        # Determine voter identity
        user = request.user if request.user.is_authenticated else None
        voter_uuid = request.data.get('voter_uuid')
        voter_ip = request.META.get('REMOTE_ADDR')

        # duplicate protection
        existing = Vote.objects.filter(poll=poll)
        if user and existing.filter(user=user).exists():
            return Response({"detail": "User has already voted."}, status=status.HTTP_400_BAD_REQUEST)
        elif voter_uuid and existing.filter(voter_uuid=voter_uuid).exists():
            return Response({"detail": "Voter has already voted."}, status=status.HTTP_400_BAD_REQUEST)
        elif voter_ip and existing.filter(voter_ip=voter_ip).exists():
            return Response({"detail": "IP has already voted."}, status=status.HTTP_400_BAD_REQUEST)

        # create vote atomically
        with transaction.atomic():
            vote = Vote.objects.create(
                poll=poll,
                option=option,
                user=user,
                voter_uuid=voter_uuid,
                voter_ip=voter_ip
            )
            Option.objects.filter(pk=option.pk).update(vote_count=F('vote_count') + 1)

        return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)


class PollResultsView(views.APIView):
    """
    Returns counts per option. Efficiently use aggregation; if Option.vote_count exists, can read directly.
    """
    permission_classes = (permissions.AllowAny,)
    def get(self, request, poll_pk):
        cache_key = f"poll_results:{poll_pk}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        poll = get_object_or_404(Poll, pk=poll_pk)
        # prefer denormalized read if available
        options = list(poll.options.all().values('id', 'text', 'vote_count'))
        payload = {"poll_id": poll.pk, "title": poll.title, "results": options}

        # cache for short duration (e.g., 5 seconds or 30 seconds depending on traffic)
        cache.set(cache_key, payload, timeout=5)
        return Response(payload)


class VoteCreateView(views.APIView):
    # Add this class or place the logic inside your existing VoteCreateView class
    permission_classes = (permissions.AllowAny,) # Adjust permissions as needed

    def post(self, request, poll_pk):
        # 1. Define/retrieve all necessary variables from the request or database
        poll = get_object_or_404(Poll, pk=poll_pk)
        option_id = request.data.get('option_id') # Get option ID from POST data
        option = get_object_or_404(Option, pk=option_id, poll=poll)
        
        user = request.user if request.user.is_authenticated else None
        # You need actual logic to get/create these if they are required fields:
        voter_uuid = "some-logic-to-get-uuid" 
        voter_ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
        
        # 2. Wrap the logic inside this POST method
        with transaction.atomic():
            vote = Vote.objects.create(
                poll=poll, 
                option=option, 
                user=user, 
                voter_uuid=voter_uuid, 
                voter_ip=voter_ip
            )
            Option.objects.filter(pk=option.pk).update(vote_count=F('vote_count') + 1)
            
            # invalidate cache
            cache_key = f"poll_results:{poll.pk}"
            cache.delete(cache_key)
            
        return Response(
            {"status": "vote recorded", "vote_id": vote.pk}, 
            status=status.HTTP_201_CREATED
        )
