from django.urls import path
from .views import VideoListCreateView, VideoDetailDestroyView
from learning.views import SummaryView, QuizView, FlashcardsView, StudyNotesView

urlpatterns = [
    path('', VideoListCreateView.as_view(), name='video_list_create'),
    path('<int:pk>/', VideoDetailDestroyView.as_view(), name='video_detail_destroy'),
    path('<int:pk>/summary/', SummaryView.as_view(), name='video_summary'),
    path('<int:pk>/quiz/', QuizView.as_view(), name='video_quiz'),
    path('<int:pk>/flashcards/', FlashcardsView.as_view(), name='video_flashcards'),
    path('<int:pk>/notes/', StudyNotesView.as_view(), name='video_notes'),
]
