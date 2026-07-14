from django.urls import path
from .views import ChatView, ConversationListView, ConversationDetailView

urlpatterns = [
    path('', ChatView.as_view(), name='chat_ask'),
    path('conversations/', ConversationListView.as_view(), name='conversation_list'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation_detail'),
]
