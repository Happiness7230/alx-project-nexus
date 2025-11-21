from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F
from django.conf import settings

class Poll(models.Model):
    """
    Poll model representing a poll with multiple options.
    """
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    allow_multiple_votes = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    def clean(self):
        """Validate poll data."""
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError("Expiry date must be in the future.")
    
    def is_expired(self):
        """Check if poll has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def is_available(self):
        """Check if poll is available for voting."""
        return self.is_active and not self.is_expired()
    
    def get_total_votes(self):
        """Get total votes across all options."""
        return Vote.objects.filter(option__poll=self).count()


class PollOption(models.Model):
    """
    Poll option model representing choices for a poll.
    """
    poll = models.ForeignKey(
        Poll, 
        on_delete=models.CASCADE, 
        related_name='poll_options_data'
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    vote_count = models.PositiveIntegerField(default=0, db_index=True)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = [['poll', 'text']]
        indexes = [
            models.Index(fields=['poll', '-vote_count']),
        ]
    
    def __str__(self):
        return f"{self.poll.title} - {self.text}"
    
    def increment_vote_count(self):
        """Atomically increment vote count."""
        PollOption.objects.filter(pk=self.pk).update(
            vote_count=F('vote_count') + 1
        )
        self.refresh_from_db()

class Option(models.Model):
    """
    Poll option model representing choices for a poll.
    """
    poll = models.ForeignKey(
        Poll, 
        on_delete=models.CASCADE, 
        related_name='options'
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    vote_count = models.PositiveIntegerField(default=0, db_index=True)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = [['poll', 'text']]
        indexes = [
            models.Index(fields=['poll', '-vote_count']),
        ]
    
    def __str__(self):
        return f"{self.poll.title} - {self.text}"
    
    def increment_vote_count(self):
        """Atomically increment vote count."""
        PollOption.objects.filter(pk=self.pk).update(
            vote_count=F('vote_count') + 1
        )
        self.refresh_from_db()


class Vote(models.Model):
    """
    Vote model tracking individual votes with duplicate prevention.
    """
    option = models.ForeignKey(
        Option, 
        on_delete=models.CASCADE, 
        related_name='votes'
    )
    voter_identifier = models.CharField(max_length=255, db_index=True)
    voted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-voted_at']
        indexes = [
            models.Index(fields=['option', 'voter_identifier']),
            models.Index(fields=['voter_identifier', '-voted_at']),
        ]
        unique_together = [['option', 'voter_identifier']]
    
    def __str__(self):
        return f"Vote for {self.option.text} by {self.voter_identifier}"
    
    def clean(self):
        """Validate vote."""
        poll = self.option.poll
        
        # Check if poll is available
        if not poll.is_available():
            raise ValidationError("This poll is no longer accepting votes.")
        
        # Check for duplicate votes if not allowed
        if not poll.allow_multiple_votes:
            existing_vote = Vote.objects.filter(
                option__poll=poll,
                voter_identifier=self.voter_identifier
            ).exclude(pk=self.pk).exists()
            
            if existing_vote:
                raise ValidationError("You have already voted in this poll.")
    
    def save(self, *args, **kwargs):
        """Override save to validate and update vote count."""
        self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.option.increment_vote_count()
