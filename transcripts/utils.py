import re
import urllib.request
import json
import logging
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)

import urllib.parse

def extract_video_id(url: str) -> str:
    """
    Extracts the YouTube video ID from various formats of YouTube URLs.
    """
    if not url:
        return ""
        
    # If it is already a video ID
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        
        # Check YouTube hostnames
        if hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com', 'web.youtube.com'):
            if parsed.path == '/watch':
                query_params = urllib.parse.parse_qs(parsed.query)
                return query_params.get('v', [''])[0]
            elif parsed.path.startswith(('/embed/', '/v/')):
                parts = parsed.path.split('/')
                if len(parts) >= 3:
                    return parts[2][:11]
        elif hostname == 'youtu.be':
            return parsed.path.strip('/')[:11]
            
        # Regex fallback
        match = re.search(r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})', url)
        if match:
            return match.group(1)
    except Exception:
        pass
        
    return ""


def fetch_youtube_metadata(video_id: str) -> dict:
    """
    Fetches basic metadata (title, channel name) for a YouTube video using the public oEmbed API.
    Does not require a YouTube API key.
    """
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {
                "title": data.get("title", "Unknown Title"),
                "channel_name": data.get("author_name", "Unknown Channel"),
                "duration": None  # oEmbed doesn't return duration, we'll estimate or leave as null
            }
    except Exception as e:
        logger.error(f"Error fetching YouTube metadata via oEmbed: {e}")
        return {
            "title": f"YouTube Video {video_id}",
            "channel_name": "YouTube",
            "duration": None
        }

def get_youtube_transcript(video_id: str) -> list:
    """
    Fetches the transcript list for a given YouTube video ID.
    Returns a list of dicts: [{'text': str, 'start': float, 'duration': float}]
    """
    try:
        api = YouTubeTranscriptApi()
        # Retrieve the transcript list
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Fallback to the first available transcript
            transcript = next(iter(transcript_list))
        
        fetched = transcript.fetch()
        
        # Convert to dictionary representation to ensure compatibility with chunking logic
        result = []
        for segment in fetched:
            if isinstance(segment, dict):
                result.append(segment)
            else:
                result.append({
                    'text': getattr(segment, 'text', ''),
                    'start': getattr(segment, 'start', 0.0),
                    'duration': getattr(segment, 'duration', 0.0)
                })
        return result
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        raise ValueError(f"Could not retrieve transcript for video {video_id}: {str(e)}")


def chunk_transcript(transcript_segments: list, max_words: int = 250, overlap_words: int = 30):
    """
    Groups individual transcript segments into larger semantic chunks.
    Ensures start and end timestamps are preserved.
    """
    chunks = []
    current_chunk_words = []
    current_chunk_start = 0.0
    current_chunk_end = 0.0
    chunk_index = 0

    for i, segment in enumerate(transcript_segments):
        text = segment['text']
        start = float(segment['start'])
        duration = float(segment.get('duration', 0.0))
        end = start + duration

        words = text.split()
        
        if not current_chunk_words:
            current_chunk_start = start

        current_chunk_words.extend(words)
        current_chunk_end = end

        # If current chunk exceeds target max_words, we complete it
        if len(current_chunk_words) >= max_words:
            chunk_text = " ".join(current_chunk_words)
            chunks.append({
                "text": chunk_text,
                "start_time": current_chunk_start,
                "end_time": current_chunk_end,
                "chunk_index": chunk_index
            })
            chunk_index += 1
            
            # Create overlap for the next chunk to preserve context at boundaries
            overlap = current_chunk_words[-overlap_words:] if len(current_chunk_words) > overlap_words else []
            current_chunk_words = list(overlap)
            # Approximate start time of the next chunk based on percentage of words remaining
            # Or just set it to the current segment start
            current_chunk_start = start

    # Append any remaining words in the final chunk
    if current_chunk_words:
        chunk_text = " ".join(current_chunk_words)
        chunks.append({
            "text": chunk_text,
            "start_time": current_chunk_start,
            "end_time": current_chunk_end,
            "chunk_index": chunk_index
        })

    return chunks

def fetch_playlist_video_ids(playlist_url: str) -> tuple[str, list[str]]:
    """
    Fetches the HTML of a public YouTube playlist and extracts all video IDs
    and the playlist title without requiring an API key.
    """
    try:
        req = urllib.request.Request(
            playlist_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64); QuestTubeAgent/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html)
        playlist_title = title_match.group(1).replace(" - YouTube", "").strip() if title_match else "YouTube Playlist"

        # Find all occurrences of "videoId":"..."
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_video_ids = []
        for vid in video_ids:
            if vid not in seen:
                seen.add(vid)
                unique_video_ids.append(vid)
                
        return playlist_title, unique_video_ids
    except Exception as e:
        logger.error(f"Error fetching playlist video IDs: {e}")
        return "YouTube Playlist", []

