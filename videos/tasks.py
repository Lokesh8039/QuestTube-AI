import logging
from django.db import transaction
from .models import Video
from transcripts.models import Transcript, TranscriptChunk
from transcripts.utils import fetch_youtube_metadata, get_youtube_transcript, chunk_transcript
from config.services.factory import get_embedding_provider

logger = logging.getLogger(__name__)

def process_video_ingestion(video_id: int):
    """
    Background job to fetch video metadata, retrieve the transcript,
    split it into chunks, generate embeddings, and save everything.
    """
    logger.info(f"Starting ingestion process for video ID: {video_id}")
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Video with ID {video_id} does not exist.")
        return

    # Update status to processing
    video.status = "processing"
    video.save()

    try:
        # 1. Fetch metadata if empty
        if not video.title or video.title.startswith("YouTube Video"):
            metadata = fetch_youtube_metadata(video.youtube_id)
            video.title = metadata.get("title", video.title)
            video.channel_name = metadata.get("channel_name", video.channel_name)
            video.save()

        # 2. Get YouTube transcript
        logger.info(f"Retrieving transcript for youtube ID: {video.youtube_id}")
        raw_segments = get_youtube_transcript(video.youtube_id)

        # 3. Create full text
        full_text = " ".join([seg['text'] for seg in raw_segments])
        
        # Determine language (default to en)
        # We can extract it if needed, otherwise stick to default 'en'
        language = "en"

        # 4. Save Transcript object
        with transaction.atomic():
            # Clear existing transcript & chunks if this is a re-run
            Transcript.objects.filter(video=video).delete()
            
            transcript_obj = Transcript.objects.create(
                video=video,
                full_text=full_text,
                language=language
            )

            # 5. Chunk transcript
            chunks_data = chunk_transcript(raw_segments)
            if not chunks_data:
                raise ValueError("No chunks were generated from the transcript.")

            # 6. Generate embeddings for all chunks in batch
            chunk_texts = [c['text'] for c in chunks_data]
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
            
            embedding_provider = get_embedding_provider()
            embeddings = embedding_provider.embed_texts(chunk_texts)

            # 7. Save Chunks with their embeddings
            chunk_objects = []
            for idx, c in enumerate(chunks_data):
                chunk_obj = TranscriptChunk(
                    transcript=transcript_obj,
                    text=c['text'],
                    start_time=c['start_time'],
                    end_time=c['end_time'],
                    chunk_index=c['chunk_index']
                )
                # Set embedding list
                chunk_obj.embedding = embeddings[idx]
                chunk_objects.append(chunk_obj)
            
            TranscriptChunk.objects.bulk_create(chunk_objects)

        # Update status to completed
        video.status = "completed"
        video.save()
        logger.info(f"Ingestion process completed successfully for video ID: {video_id}")

    except Exception as e:
        logger.exception(f"Failed to process video {video_id}: {e}")
        video.status = "failed"
        video.save()
