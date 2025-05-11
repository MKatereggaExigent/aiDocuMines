from django.urls import path
from .views import  FileEventLogView

urlpatterns = [
    # File Events
    path("file-events/", FileEventLogView.as_view(), name="file-event-log"),
]
