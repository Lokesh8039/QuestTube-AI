import json
import re
import logging
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from videos.models import Video
from transcripts.models import Transcript
from config.services.factory import get_llm_provider
from config.services.providers import RateLimitError, ServiceUnavailableError

logger = logging.getLogger(__name__)

def clean_json_response(raw_text: str) -> str:
    """
    Cleans markdown code blocks (e.g. ```json ... ```) from LLM responses to extract raw JSON.
    """
    cleaned = raw_text.strip()
    # Remove ```json ... ``` tags
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()

class SummaryView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        video = get_object_or_404(Video, id=pk, user=request.user)
        summary_type = request.data.get("summary_type", "detailed").lower()

        if summary_type not in ("short", "detailed", "bullet_points", "chapter_wise"):
            summary_type = "detailed"

        try:
            transcript = video.transcript
        except Transcript.DoesNotExist:
            return Response({"error": "Transcript has not been fetched or does not exist for this video."}, status=status.HTTP_400_BAD_REQUEST)

        system_instruction = (
            "You are an expert educator. Your task is to summarize the provided YouTube transcript.\n"
            f"Generate a {summary_type} summary. Rely ONLY on the provided text. Do not use external knowledge.\n"
            "Format your output in clean, readable markdown."
        )

        prompt = f"Transcript:\n{transcript.full_text[:60000]}"  # Cap at 60k chars to prevent excessive token use

        try:
            llm_provider = get_llm_provider()
            summary = llm_provider.generate(prompt, system_instruction=system_instruction)
            return Response({
                "video_id": video.id,
                "summary_type": summary_type,
                "summary": summary
            })
        except RateLimitError as rle:
            logger.warning(f"Summary generation rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ServiceUnavailableError as sue:
            logger.warning(f"Summary generation service unavailable: {sue}")
            return Response({"error": str(sue)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return Response({"error": f"Failed to generate summary: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuizView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        video = get_object_or_404(Video, id=pk, user=request.user)
        difficulty = request.data.get("difficulty", "intermediate")
        num_questions = request.data.get("questions", 5)

        try:
            transcript = video.transcript
        except Transcript.DoesNotExist:
            return Response({"error": "Transcript does not exist for this video."}, status=status.HTTP_400_BAD_REQUEST)

        system_instruction = (
            "You are an expert educator. Generate a multiple choice quiz based strictly on the provided transcript.\n"
            f"Difficulty: {difficulty}. Number of questions: {num_questions}.\n"
            "You MUST output the result as a raw JSON array of objects. Do not include markdown code block syntax (like ```json).\n"
            "Each object must have these exact keys:\n"
            "- 'question': the question text\n"
            "- 'options': an array of 4 choices (e.g. ['A) ...', 'B) ...', 'C) ...', 'D) ...'])\n"
            "- 'answer': the letter of the correct option (e.g. 'A', 'B', 'C', 'D')"
        )

        prompt = f"Transcript:\n{transcript.full_text[:60000]}"

        try:
            llm_provider = get_llm_provider()
            quiz_raw = llm_provider.generate(prompt, system_instruction=system_instruction)
            
            cleaned = clean_json_response(quiz_raw)
            quiz_json = json.loads(cleaned)
            return Response(quiz_json)
        except RateLimitError as rle:
            logger.warning(f"Quiz generation rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ServiceUnavailableError as sue:
            logger.warning(f"Quiz generation service unavailable: {sue}")
            return Response({"error": str(sue)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}. Raw response: {quiz_raw if 'quiz_raw' in locals() else 'None'}")
            return Response({
                "error": "Failed to generate quiz as structured JSON. Returning raw text.",
                "raw_content": quiz_raw if 'quiz_raw' in locals() else str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FlashcardsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        video = get_object_or_404(Video, id=pk, user=request.user)

        try:
            transcript = video.transcript
        except Transcript.DoesNotExist:
            return Response({"error": "Transcript does not exist for this video."}, status=status.HTTP_400_BAD_REQUEST)

        system_instruction = (
            "You are an expert educator. Generate study flashcards based strictly on the provided transcript.\n"
            "You MUST output the result as a raw JSON array of objects. Do not include markdown code block formatting.\n"
            "Each object must have these exact keys:\n"
            "- 'front': the question, term, or prompt\n"
            "- 'back': the answer, explanation, or definition"
        )

        prompt = f"Transcript:\n{transcript.full_text[:60000]}"

        try:
            llm_provider = get_llm_provider()
            flashcards_raw = llm_provider.generate(prompt, system_instruction=system_instruction)
            
            cleaned = clean_json_response(flashcards_raw)
            flashcards_json = json.loads(cleaned)
            return Response(flashcards_json)
        except RateLimitError as rle:
            logger.warning(f"Flashcards generation rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ServiceUnavailableError as sue:
            logger.warning(f"Flashcards generation service unavailable: {sue}")
            return Response({"error": str(sue)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Flashcards generation failed: {e}")
            return Response({
                "error": "Failed to generate flashcards as structured JSON.",
                "raw_content": flashcards_raw if 'flashcards_raw' in locals() else str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudyNotesView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        video = get_object_or_404(Video, id=pk, user=request.user)

        try:
            transcript = video.transcript
        except Transcript.DoesNotExist:
            return Response({"error": "Transcript does not exist for this video."}, status=status.HTTP_400_BAD_REQUEST)

        system_instruction = (
            "You are an expert educator. Create comprehensive study notes based strictly on the provided transcript.\n"
            "Organize them using markdown headers, bullet points, key terminology bolded, and a section for summary takeaways."
        )

        prompt = f"Transcript:\n{transcript.full_text[:60000]}"

        try:
            llm_provider = get_llm_provider()
            notes = llm_provider.generate(prompt, system_instruction=system_instruction)
            return Response({
                "video_id": video.id,
                "notes": notes
            })
        except RateLimitError as rle:
            logger.warning(f"Notes generation rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ServiceUnavailableError as sue:
            logger.warning(f"Notes generation service unavailable: {sue}")
            return Response({"error": str(sue)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Notes generation failed: {e}")
            return Response({"error": f"Failed to generate study notes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
