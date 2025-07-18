# integrations/urls.py

from django.urls import path
from .views import NextcloudAutologinView, NextcloudRedirectView, IntegrationLogListView

app_name = "integrations"

urlpatterns = [
    path("nextcloud-autologin/", NextcloudAutologinView.as_view(), name="nextcloud-autologin"),
    path("nextcloud-redirect/", NextcloudRedirectView.as_view(), name="nextcloud-redirect"),
    path('logs/', IntegrationLogListView.as_view(), name='integration-log-list'),
]

