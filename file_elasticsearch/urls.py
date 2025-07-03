# file_elasticsearch/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('delete-index/', views.DeleteIndexView.as_view()),
    path('force-reindex/', views.ForceReindexView.as_view()),
    path('index/<int:file_id>/', views.IndexSingleFileView.as_view()),
    path('search/', views.SearchView.as_view()),
    path('advanced-search/', views.AdvancedSearchView.as_view()),
]

