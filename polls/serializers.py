from rest_framework import serializers
from django.utils import timezone
from django.db import models
from .models import Poll, Option, PollOption, Vote

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'vote_count']

class PollSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'created_at', 'expires_at', 'is_active', 'options']

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        poll = Poll.objects.create(**validated_data)
        Option.objects.bulk_create([Option(poll=poll, **o) for o in options_data])
        return poll

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'poll', 'option', 'user', 'voter_uuid', 'voter_ip', 'created_at']
        read_only_fields = ['created_at']

class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for poll options."""
    percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'order', 'vote_count', 'percentage']
        read_only_fields = ['id', 'vote_count', 'percentage']
    
    def get_percentage(self, obj):
        """Calculate vote percentage."""
        total_votes = obj.poll.get_total_votes()
        if total_votes == 0:
            return 0.0
        return round((obj.vote_count / total_votes) * 100, 2)


class PollOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating poll options."""
    
    class Meta:
        model = PollOption
        fields = ['text', 'order']


class PollListSerializer(serializers.ModelSerializer):
    """Serializer for listing polls."""
    total_votes = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    options_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Poll
        fields = [
            'id', 'title', 'description', 'created_at', 'expires_at',
            'is_active', 'is_expired', 'total_votes', 'options_count'
        ]
    
    def get_total_votes(self, obj):
        return obj.get_total_votes()
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_options_count(self, obj):
        return obj.options.count()


class PollDetailSerializer(serializers.ModelSerializer):
    """Serializer for poll details with options."""
    options = PollOptionSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Poll
        fields = [
            'id', 'title', 'description', 'created_at', 'expires_at',
            'is_active', 'allow_multiple_votes', 'created_by',
            'is_expired', 'is_available', 'total_votes', 'options'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_total_votes(self, obj):
        return obj.get_total_votes()
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_is_available(self, obj):
        return obj.is_available()


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls with options."""
    options = PollOptionCreateSerializer(many=True)
    
    class Meta:
        model = Poll
        fields = [
            'title', 'description', 'expires_at', 'is_active',
            'allow_multiple_votes', 'created_by', 'options'
        ]
    
    def validate_options(self, value):
        """Validate that at least 2 options are provided."""
        if len(value) < 2:
            raise serializers.ValidationError(
                "Poll must have at least 2 options."
            )
        return value
    
    def validate_expires_at(self, value):
        """Validate expiry date is in the future."""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "Expiry date must be in the future."
            )
        return value
    
    def create(self, validated_data):
        """Create poll with options."""
        options_data = validated_data.pop('options')
        poll = Poll.objects.create(**validated_data)
        
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)
        
        return poll


class VoteSerializer(serializers.ModelSerializer):
    """Serializer for voting."""
    option_id = serializers.IntegerField(write_only=True)
    poll_id = serializers.SerializerMethodField(read_only=True)
    option_text = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Vote
        fields = [
            'id', 'option_id', 'poll_id', 'option_text',
            'voter_identifier', 'voted_at'
        ]
        read_only_fields = ['id', 'voted_at', 'poll_id', 'option_text']
    
    def get_poll_id(self, obj):
        return obj.option.poll.id
    
    def get_option_text(self, obj):
        return obj.option.text
    
    def validate_option_id(self, value):
        """Validate option exists."""
        try:
            option = PollOption.objects.select_related('poll').get(pk=value)
            
            # Check if poll is available
            if not option.poll.is_available():
                raise serializers.ValidationError(
                    "This poll is no longer accepting votes."
                )
            
            return value
        except PollOption.DoesNotExist:
            raise serializers.ValidationError("Invalid option ID.")
    
    def validate(self, data):
        """Validate duplicate votes."""
        option = PollOption.objects.select_related('poll').get(
            pk=data['option_id']
        )
        poll = option.poll
        voter_id = data['voter_identifier']
        
        # Check for duplicate votes if not allowed
        if not poll.allow_multiple_votes:
            existing_vote = Vote.objects.filter(
                option__poll=poll,
                voter_identifier=voter_id
            ).exists()
            
            if existing_vote:
                raise serializers.ValidationError({
                    'voter_identifier': 'You have already voted in this poll.'
                })
        
        return data
    
    def create(self, validated_data):
        """Create vote with option object."""
        option_id = validated_data.pop('option_id')
        option = PollOption.objects.get(pk=option_id)
        vote = Vote.objects.create(option=option, **validated_data)
        return vote


class PollResultSerializer(serializers.ModelSerializer):
    """Serializer for poll results."""
    options = PollOptionSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    winner = serializers.SerializerMethodField()
    
    class Meta:
        model = Poll
        fields = [
            'id', 'title', 'description', 'total_votes',
            'options', 'winner', 'created_at', 'expires_at'
        ]
    
    def get_total_votes(self, obj):
        return obj.get_total_votes()
    
    def get_winner(self, obj):
        """Get the option(s) with the most votes."""
        max_votes = obj.options.aggregate(
            models.Max('vote_count')
        )['vote_count__max']
        
        if max_votes == 0:
            return None
        
        winners = obj.options.filter(vote_count=max_votes)
        return PollOptionSerializer(winners, many=True).data
