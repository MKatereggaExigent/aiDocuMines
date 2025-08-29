# insights_hub/urls.py
from django.urls import path
from .views import InsightsView, InsightsTaskStatusView

urlpatterns = [
    path("", InsightsView.as_view(), name="insights"),
    path("tasks/<uuid:task_id>/", InsightsTaskStatusView.as_view(), name="insights-task"),
]

