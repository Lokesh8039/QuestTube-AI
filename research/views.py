import logging
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from knowledge_base.services import semantic_search
from config.services.factory import get_llm_provider
from config.services.providers import RateLimitError
from videos.models import Video

logger = logging.getLogger(__name__)

class VideoComparisonView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        video_ids = request.data.get("video_ids", [])
        topic = request.data.get("topic")

        if not video_ids:
            return Response({"error": "At least one video_id must be provided."}, status=status.HTTP_400_BAD_REQUEST)
        if not topic:
            return Response({"error": "Comparison topic is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Retrieve video details
        videos = Video.objects.filter(id__in=video_ids, user=request.user)
        if not videos.exists():
            return Response({"error": "No valid videos found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Retrieve semantic context matching the topic across the videos
        search_results = semantic_search(topic, video_ids, top_k=10)
        
        # Group chunks by video
        video_contexts = {}
        for item in search_results:
            chunk = item["chunk"]
            v = chunk.transcript.video
            if v.id not in video_contexts:
                video_contexts[v.id] = {
                    "title": v.title,
                    "chunks": []
                }
            video_contexts[v.id]["chunks"].append(f"[{chunk.start_time:.1f}s]: {chunk.text}")

        # 3. Format the comparison prompt
        context_str = ""
        for vid_id, data in video_contexts.items():
            context_str += f"\nVIDEO: {data['title']}\n"
            context_str += "\n".join(data["chunks"])
            context_str += "\n--------------------\n"

        system_instruction = (
            "You are an expert Research Assistant. Your task is to compare and contrast the content of the selected videos side-by-side on the requested topic.\n"
            "Answer using ONLY the provided transcript snippets. Do not use external knowledge.\n"
            "Format the response in structured markdown with a clear Comparison per video, a Side-by-Side Analysis, and a Conclusion summarizing the main differences.\n"
            "Make sure to reference source timestamps."
        )

        prompt = (
            f"Topic: Compare the videos on '{topic}'\n\n"
            f"Video Transcript Context:\n{context_str or 'No relevant snippets found.'}\n"
        )

        try:
            llm_provider = get_llm_provider()
            comparison_response = llm_provider.generate(prompt, system_instruction=system_instruction)
            return Response({
                "topic": topic,
                "comparison": comparison_response
            })
        except RateLimitError as rle:
            logger.warning(f"Comparison rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            logger.error(f"Comparison generation failed: {e}")
            return Response({"error": f"Failed to generate comparison: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContradictionDetectorView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        video_ids = request.data.get("video_ids", [])
        if not video_ids:
            return Response({"error": "At least one video_id must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch relevant snippets from all selected videos on general themes to look for contradictions
        search_results = semantic_search("limitations performance issues advantages disadvantages opinions choices", video_ids, top_k=15)
        
        video_contexts = {}
        for item in search_results:
            chunk = item["chunk"]
            v = chunk.transcript.video
            if v.id not in video_contexts:
                video_contexts[v.id] = {
                    "title": v.title,
                    "chunks": []
                }
            video_contexts[v.id]["chunks"].append(f"[{chunk.start_time:.1f}s]: {chunk.text}")

        context_str = ""
        for vid_id, data in video_contexts.items():
            context_str += f"\nVIDEO: {data['title']}\n"
            context_str += "\n".join(data["chunks"])
            context_str += "\n--------------------\n"

        system_instruction = (
            "You are an expert Research Assistant. Your job is to analyze the transcripts and identify any Potential Contradictions, "
            "factual disagreements, or conflicting claims between the selected videos.\n"
            "If they conflict (e.g. Video A says framework X is slow, Video B says framework X is very fast), explain the conflict and cite timestamps.\n"
            "If no contradictions are found, explain how their viewpoints align or complement each other.\n"
            "Rely ONLY on the provided video contexts. Do not use external knowledge."
        )

        prompt = (
            f"Analyze the following video transcript snippets for contradictions or alignments:\n\n"
            f"{context_str or 'No video context found.'}\n"
        )

        try:
            llm_provider = get_llm_provider()
            contradiction_response = llm_provider.generate(prompt, system_instruction=system_instruction)
            return Response({
                "analysis": contradiction_response
            })
        except RateLimitError as rle:
            logger.warning(f"Contradiction detection rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}")
            return Response({"error": f"Failed to generate contradiction analysis: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResearchReportView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        video_ids = request.data.get("video_ids", [])
        topic = request.data.get("topic", "General Analysis")

        if not video_ids:
            return Response({"error": "At least one video_id must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve a wide range of chunks for the report
        search_results = semantic_search(topic, video_ids, top_k=15)
        
        video_contexts = {}
        for item in search_results:
            chunk = item["chunk"]
            v = chunk.transcript.video
            if v.id not in video_contexts:
                video_contexts[v.id] = {
                    "title": v.title,
                    "chunks": []
                }
            video_contexts[v.id]["chunks"].append(f"[{chunk.start_time:.1f}s]: {chunk.text}")

        context_str = ""
        for vid_id, data in video_contexts.items():
            context_str += f"\nVIDEO: {data['title']}\n"
            context_str += "\n".join(data["chunks"])
            context_str += "\n--------------------\n"

        system_instruction = (
            "You are an expert Research Assistant. Your job is to compile a comprehensive, highly detailed Research Report "
            "on the topic based ONLY on the provided transcript snippets.\n"
            "The report MUST be structured in markdown with the following sections:\n"
            "1. Introduction\n"
            "2. Key Themes Found\n"
            "3. Detailed Evidence/Analysis (grouped by sub-topics or videos)\n"
            "4. Conflicting Claims or Alignments\n"
            "5. Conclusion\n"
            "CITE references with video titles and timestamps throughout the text."
        )

        prompt = (
            f"Topic: {topic}\n\n"
            f"Video Transcript Context:\n{context_str or 'No context found.'}\n"
        )

        try:
            llm_provider = get_llm_provider()
            report_response = llm_provider.generate(prompt, system_instruction=system_instruction)
            return Response({
                "topic": topic,
                "report": report_response
            })
        except RateLimitError as rle:
            logger.warning(f"Research report rate limit hit: {rle}")
            return Response({"error": str(rle)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            logger.error(f"Research report generation failed: {e}")
            return Response({"error": f"Failed to generate research report: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
