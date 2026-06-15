from django.urls import path
from .views import (
    health_check,
    AutomationTemplateListCreateView,
    AutomationTemplateDetailView,
    SubmitAutomationAPIView,
    CheckAutomationStatusAPIView,
    DownloadAutomationResultAPIView,
    ClauseCategoryListCreateView,
    ClauseListCreateView,
    ClauseDetailView,
    TemplateFieldExtractView,
    BulkSubmitAutomationAPIView,
)

urlpatterns = [
    path("templates/", AutomationTemplateListCreateView.as_view(), name="automation-template-list-create"),
    path("templates/<uuid:pk>/", AutomationTemplateDetailView.as_view(), name="automation-template-detail"),
    path("submit-automation/", SubmitAutomationAPIView.as_view(), name="submit-automation"),
    path("check-automation-status/", CheckAutomationStatusAPIView.as_view(), name="check-automation-status"),
    path("download-automation-result/", DownloadAutomationResultAPIView.as_view(), name="download-automation-result"),
    path("health/", health_check, name="health_check"),
    path("clause-categories/", ClauseCategoryListCreateView.as_view(), name="clause-category-list-create"),
    path("clauses/", ClauseListCreateView.as_view(), name="clause-list-create"),
    path("clauses/<uuid:pk>/", ClauseDetailView.as_view(), name="clause-detail"),
    path("template-fields/", TemplateFieldExtractView.as_view(), name="template-field-extract"),
    path("bulk-submit-automation/", BulkSubmitAutomationAPIView.as_view(), name="bulk-submit-automation"),
]
