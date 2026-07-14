from rest_framework import serializers
from .models import Video, Playlist

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('id', 'youtube_id', 'title', 'url', 'channel_name', 'duration', 'status', 'created_at', 'playlist')
        read_only_fields = ('id', 'youtube_id', 'title', 'channel_name', 'duration', 'status', 'created_at', 'playlist')

class PlaylistSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = ('id', 'title', 'url', 'created_at', 'videos')
        read_only_fields = ('id', 'title', 'created_at', 'videos')
