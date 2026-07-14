from django.test import TestCase
from unittest.mock import patch
from django.contrib.auth.models import User
from videos.models import Video
from transcripts.models import Transcript, TranscriptChunk
from transcripts.utils import chunk_transcript, extract_video_id
from knowledge_base.services import compute_cosine_similarity, semantic_search

class TranscriptUtilsTests(TestCase):
    def test_extract_video_id(self):
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://invalid-url.com/abc"), "")

    def test_chunk_transcript(self):
        # Create a mock transcript with 10 segments
        segments = [
            {"text": f"word{i} hello world is a standard test string containing multiple elements", "start": float(i * 10), "duration": 5.0}
            for i in range(10)
        ]
        
        # Max words = 15, overlap = 2
        chunks = chunk_transcript(segments, max_words=15, overlap_words=2)
        
        self.assertTrue(len(chunks) > 1)
        self.assertEqual(chunks[0]['chunk_index'], 0)
        self.assertEqual(chunks[0]['start_time'], 0.0)
        # Verify that start/end values are float numbers
        self.assertIsInstance(chunks[0]['start_time'], float)
        self.assertIsInstance(chunks[0]['end_time'], float)

class VectorSearchTests(TestCase):
    def test_compute_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]  # Exact match
        self.assertAlmostEqual(compute_cosine_similarity(v1, v2), 1.0)
        
        v3 = [0.0, 1.0, 0.0]  # Orthogonal
        self.assertAlmostEqual(compute_cosine_similarity(v1, v3), 0.0)
        
        v4 = [-1.0, 0.0, 0.0] # Opposite
        self.assertAlmostEqual(compute_cosine_similarity(v1, v4), -1.0)

    @patch('knowledge_base.services.get_embedding_provider')
    def test_semantic_search_flow(self, mock_get_provider):
        # Set up mock embedding provider
        class MockEmbeddingProvider:
            def embed_text(self, text):
                # Return static embedding depending on query
                if "apple" in text:
                    return [1.0, 0.0, 0.0]
                return [0.0, 1.0, 0.0]
            
        mock_get_provider.return_value = MockEmbeddingProvider()

        # Create dummy database data
        user = User.objects.create_user(username="testsearchuser", password="password")
        video = Video.objects.create(
            user=user, 
            youtube_id="vid123", 
            title="Fruit Video", 
            url="https://youtube.com/watch?v=vid123",
            status="completed"
        )
        transcript = Transcript.objects.create(video=video, full_text="apple banana")
        
        chunk1 = TranscriptChunk.objects.create(
            transcript=transcript,
            text="I love apples very much.",
            start_time=0.0,
            end_time=10.0,
            chunk_index=0
        )
        chunk1.embedding = [0.9, 0.1, 0.0]  # Vector close to [1.0, 0.0, 0.0]
        chunk1.save()

        chunk2 = TranscriptChunk.objects.create(
            transcript=transcript,
            text="Here is a description of bananas.",
            start_time=10.0,
            end_time=20.0,
            chunk_index=1
        )
        chunk2.embedding = [0.1, 0.9, 0.0]  # Vector far from [1.0, 0.0, 0.0]
        chunk2.save()

        # Perform semantic search for "apple"
        results = semantic_search("apple", [video.id], top_k=5)
        
        self.assertEqual(len(results), 2)
        # First chunk should be scored higher because of similarity with query vector [1.0, 0.0, 0.0]
        self.assertEqual(results[0]["chunk"].id, chunk1.id)
        self.assertTrue(results[0]["score"] > results[1]["score"])
