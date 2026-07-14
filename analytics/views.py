from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.db.models import Sum, Count
from .models import TokenUsage, QueryLog

class AnalyticsSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        # Aggregate token usage for user
        tokens_agg = TokenUsage.objects.filter(user=user).aggregate(
            total_prompt=Sum('prompt_tokens'),
            total_completion=Sum('completion_tokens'),
            total=Sum('total_tokens'),
            count=Count('id')
        )
        
        # Aggregate query log count for user
        queries_agg = QueryLog.objects.filter(user=user).aggregate(
            total_queries=Count('id')
        )

        # Usage by provider
        provider_usage = TokenUsage.objects.filter(user=user).values('provider').annotate(
            total_tokens=Sum('total_tokens')
        )

        return Response({
            "total_tokens_used": tokens_agg["total"] or 0,
            "prompt_tokens_used": tokens_agg["total_prompt"] or 0,
            "completion_tokens_used": tokens_agg["total_completion"] or 0,
            "total_calls": tokens_agg["count"] or 0,
            "total_queries": queries_agg["total_queries"] or 0,
            "provider_breakdown": list(provider_usage)
        })
