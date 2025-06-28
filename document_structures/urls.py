# document_structures/urls.py

from django.urls import path
from document_structures import views

urlpatterns = [
    path(
        "document-structure/submit/",
        views.SubmitDocumentPartitionAPIView.as_view(),
        name="document-structure-submit",
    ),
    path(
        "document-structure/status/",
        views.DocumentStructureRunStatusAPIView.as_view(),
        name="document-structure-status",
    ),
    path(
        "document-structure/compare/",
        views.SubmitDocumentComparisonAPIView.as_view(),
        name="document-structure-compare",
    ),
    path(
        "document-structure/compare/status/",
        views.DocumentComparisonStatusAPIView.as_view(),
        name="document-structure-compare-status",
    ),
]

