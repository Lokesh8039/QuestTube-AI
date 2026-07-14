from django.db import models
from django.contrib.auth.models import User

class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField(max_length=500, blank=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.url

class Video(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="videos")
    playlist = models.ForeignKey(Playlist, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos")
    youtube_id = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    url = models.URLField()
    channel_name = models.CharField(max_length=255, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # in seconds
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
