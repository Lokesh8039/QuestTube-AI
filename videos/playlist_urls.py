from django.urls import path
from .views import PlaylistListView, PlaylistDetailView, PlaylistImportView

urlpatterns = [
    path('', PlaylistListView.as_view(), name='playlist_list'),
    path('<int:pk>/', PlaylistDetailView.as_view(), name='playlist_detail'),
    path('import/', PlaylistImportView.as_view(), name='playlist_import'),
]
