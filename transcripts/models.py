import json
from django.db import models
from videos.models import Video

class Transcript(models.Model):
    video = models.OneToOneField(
        Video,
        on_delete=models.CASCADE,
        related_name="transcript"
    )
    full_text = models.TextField()
    language = models.CharField(max_length=20, default="en")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript for {self.video.title}"

class TranscriptChunk(models.Model):
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    text = models.TextField()
    start_time = models.FloatField()  # in seconds
    end_time = models.FloatField()    # in seconds
    chunk_index = models.IntegerField()
    embedding_json = models.TextField(db_column="embedding", blank=True, null=True)

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.transcript.video.title}"

    @property
    def embedding(self):
        if not self.embedding_json:
            return []
        try:
            return json.loads(self.embedding_json)
        except Exception:
            return []

    @embedding.setter
    def embedding(self, val):
        if val is None:
            self.embedding_json = "[]"
        else:
            self.embedding_json = json.dumps(val)
