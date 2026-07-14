import json
from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.title}"

class Message(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    sources_json = models.TextField(default="[]")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role.capitalize()} message in {self.conversation.title}"

    @property
    def sources(self):
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources.setter
    def sources(self, val):
        self.sources_json = json.dumps(val or [])
