import logging
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .serializers import ConversationSerializer, ConversationDetailSerializer, MessageSerializer
from knowledge_base.services import semantic_search
from config.services.factory import get_llm_provider
from config.services.providers import RateLimitError
from analytics.models import TokenUsage, QueryLog

logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    sec = int(seconds)
    hrs = sec // 3600
    mins = (sec % 3600) // 60
    secs = sec % 60
    if hrs > 0:
        return f"{hrs:02}:{mins:02}:{secs:02}"
    return f"{mins:02}:{secs:02}"

class ChatView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        question = request.data.get("question")
        video_ids = request.data.get("video_ids", [])
        conversation_id = request.data.get("conversation_id")

        if not question:
            return Response({"error": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not video_ids:
            return Response({"error": "At least one video_id must be selected."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Retrieve or create conversation
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        else:
            # Generate auto-title from first 40 chars of question
            title = question[:40] + "..." if len(question) > 40 else question
            conversation = Conversation.objects.create(user=request.user, title=title)

        # Save the user's message
        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # 2. Semantic Search
        search_results = semantic_search(question, video_ids, top_k=5)
        
        # 3. Format context & track sources
        context_items = []
        sources = []
        
        for item in search_results:
            chunk = item["chunk"]
            score = item["score"]
            video = chunk.transcript.video
            
            # Format timestamp
            timestamp_str = format_timestamp(chunk.start_time)
            
            context_text = (
                f"Source Video: {video.title}\n"
                f"Timestamp: {timestamp_str}\n"
                f"Content: {chunk.text}\n"
            )
            context_items.append(context_text)
            
            # Add to response sources metadata
            sources.append({
                "video_id": video.id,
                "title": video.title,
                "timestamp": chunk.start_time,
                "timestamp_formatted": timestamp_str,
                "score": round(score, 4)
            })

        context_block = "\n---\n".join(context_items)

        # 4. Prompt Engineering
        system_instruction = (
            "You are an expert YouTube Research Assistant. Your task is to answer the user's query.\n"
            "You MUST answer the question using ONLY the provided YouTube Video Transcripts in the context.\n"
            "If the provided context does not contain the answer, state that the selected videos do not have enough information to answer.\n"
            "Do not make up facts, guess, or use external knowledge.\n"
            "For each factual point in your answer, you MUST cite the source video name and timestamp (e.g. [Video Title - MM:SS])."
        )
        
        prompt = (
            f"User Question:\n{question}\n\n"
            f"Provided Video Transcript Context:\n"
            f"{context_block or 'No transcript context found.'}\n"
        )

        # 5. Get LLM Response
        try:
            llm_provider = get_llm_provider()
            answer = llm_provider.generate(prompt, system_instruction=system_instruction)
        except RateLimitError as rle:
            logger.warning(f"RAG LLM rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            logger.error(f"RAG LLM generation failed: {e}")
            return Response({"error": "Failed to generate answer from AI provider."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer
        )
        assistant_message.sources = sources
        assistant_message.save()

        # 6. Log Analytics (Token counts estimated if api doesn't return, or simple logs)
        try:
            # We estimate 1 token ≈ 4 characters for basic cost estimation
            input_tokens = len(prompt + system_instruction) // 4
            output_tokens = len(answer) // 4
            
            TokenUsage.objects.create(
                user=request.user,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                provider=llm_provider.__class__.__name__.replace("Provider", "").lower()
            )
            
            QueryLog.objects.create(
                user=request.user,
                query=question,
                response=answer,
                video_count=len(video_ids)
            )
        except Exception as e:
            logger.error(f"Failed to log query analytics: {e}")

        return Response({
            "conversation_id": conversation.id,
            "answer": answer,
            "sources": sources
        })

class ConversationListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

class ConversationDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)

    def delete(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
