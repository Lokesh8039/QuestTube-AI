from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .models import Video, Playlist
from .serializers import VideoSerializer, PlaylistSerializer
from transcripts.utils import extract_video_id, fetch_playlist_video_ids
from .tasks import process_video_ingestion
from config.services.background_utils import run_background_task

class VideoListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        videos = Video.objects.filter(user=request.user)
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response({"error": "URL is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        youtube_id = extract_video_id(url)
        if not youtube_id:
            return Response({"error": "Invalid YouTube URL."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already added this video
        video, created = Video.objects.get_or_create(
            user=request.user,
            youtube_id=youtube_id,
            defaults={
                "title": f"YouTube Video {youtube_id}",
                "url": url,
                "status": "pending"
            }
        )

        # Trigger processing if newly created or failed previously
        if created or video.status in ("failed", "pending"):
            video.status = "pending"
            video.save()
            run_background_task(process_video_ingestion, video.id)

        serializer = VideoSerializer(video)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class VideoDetailDestroyView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        try:
            video = Video.objects.get(pk=pk, user=request.user)
        except Video.DoesNotExist:
            return Response({"error": "Video not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VideoSerializer(video)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            video = Video.objects.get(pk=pk, user=request.user)
        except Video.DoesNotExist:
            return Response({"error": "Video not found."}, status=status.HTTP_404_NOT_FOUND)
        video.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PlaylistListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        playlists = Playlist.objects.filter(user=request.user)
        serializer = PlaylistSerializer(playlists, many=True)
        return Response(serializer.data)

class PlaylistDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        try:
            playlist = Playlist.objects.get(pk=pk, user=request.user)
        except Playlist.DoesNotExist:
            return Response({"error": "Playlist not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PlaylistSerializer(playlist)
        return Response(serializer.data)

class PlaylistImportView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        playlist_url = request.data.get("playlist_url")
        if not playlist_url:
            return Response({"error": "playlist_url is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Fetch video IDs and title from playlist
        playlist_title, video_ids = fetch_playlist_video_ids(playlist_url)
        if not video_ids:
            return Response({"error": "Could not extract videos from playlist or playlist is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Create Playlist object
        with transaction.atomic():
            playlist = Playlist.objects.create(
                user=request.user,
                title=playlist_title,
                url=playlist_url
            )

            # 3. Create Video objects
            videos_to_process = []
            for yid in video_ids:
                # Reuse existing user video if already added, otherwise create
                video, created = Video.objects.get_or_create(
                    user=request.user,
                    youtube_id=yid,
                    defaults={
                        "title": f"YouTube Video {yid}",
                        "url": f"https://www.youtube.com/watch?v={yid}",
                        "status": "pending",
                        "playlist": playlist
                    }
                )
                if not created and not video.playlist:
                    video.playlist = playlist
                    video.save()
                
                if created or video.status in ("failed", "pending"):
                    video.status = "pending"
                    video.save()
                    videos_to_process.append(video.id)

        # 4. Trigger background task for each video
        for vid_id in videos_to_process:
            run_background_task(process_video_ingestion, vid_id)

        serializer = PlaylistSerializer(playlist)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
