from django.urls import path
from .views import VideoComparisonView, ContradictionDetectorView, ResearchReportView

urlpatterns = [
    path('compare/', VideoComparisonView.as_view(), name='research_compare'),
    path('contradictions/', ContradictionDetectorView.as_view(), name='research_contradictions'),
    path('report/', ResearchReportView.as_view(), name='research_report'),
]
