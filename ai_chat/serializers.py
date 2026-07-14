from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sources = serializers.ReadOnlyField()

    class Meta:
        model = Message
        fields = ('id', 'role', 'content', 'sources', 'created_at')

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ('id', 'title', 'created_at')

class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'title', 'created_at', 'messages')
