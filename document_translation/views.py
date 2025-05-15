from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from oauth2_provider.models import Application
from core.models import File
from document_translation.models import TranslationRun, TranslationFile, TranslationLanguage
from document_translation.tasks import (
    translate_document_task,
    check_translation_status_task,
    download_translated_file_task
)
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import os
from rest_framework.permissions import AllowAny
from rest_framework import generics
from document_translation.serializers import TranslationFileSerializer

from django.http import FileResponse, Http404
from django.utils.encoding import smart_str


logger = logging.getLogger(__name__)

User = get_user_model()

# ✅ Define Swagger parameters
client_id_param = openapi.Parameter(
    "X-Client-ID", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True, description="Client ID for authentication"
)
client_secret_param = openapi.Parameter(
    "X-Client-Secret", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True, description="Client Secret for authentication"
)
file_id_param = openapi.Parameter(
    "file_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Unique File ID"
)
translation_run_id_param = openapi.Parameter(
    "translation_run_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Unique translation_run_id to track translation."
)
from_language_param = openapi.Parameter(
    "from_language", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Source language code"
)
to_language_param = openapi.Parameter(
    "to_language", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Target language code"
)


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({"status": "ok"}, status=200)

def get_user_from_client_id(client_id):
    """Retrieves the User associated with a given `client_id` from OAuth2 Application."""
    try:
        application = Application.objects.get(client_id=client_id)
        return application.user
    except Application.DoesNotExist:
        return None


### **🔹 Submit Translation**
class SubmitTranslationAPIView(APIView):
    """
    Submit a file for translation and track using `file_id` and `translation_run_id`.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Submit a file for translation.",
        tags=["Translation"],
        manual_parameters=[
            client_id_param, client_secret_param, file_id_param, from_language_param, to_language_param
        ],
    )
    def post(self, request):
        client_id = request.headers.get("X-Client-ID")
        client_secret = request.headers.get("X-Client-Secret")
        file_id = request.query_params.get("file_id")
        from_lang = request.query_params.get("from_language")
        to_lang = request.query_params.get("to_language")

        if not all([client_id, client_secret, file_id, from_lang, to_lang]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Get user from client_id
        user = get_user_from_client_id(client_id)
        if not user:
            return Response({"error": "Invalid client ID"}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ Get the file instance
        file_instance = get_object_or_404(File, id=file_id)

        if file_instance.user != user:
            raise PermissionDenied("You are not authorized to translate this file.")

        if not os.path.exists(file_instance.filepath):
            return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Validate source and target languages
        if not TranslationLanguage.objects.filter(code=from_lang).exists():
            return Response({"error": f"Invalid source language: {from_lang}"}, status=status.HTTP_400_BAD_REQUEST)
        if not TranslationLanguage.objects.filter(code=to_lang).exists():
            return Response({"error": f"Invalid target language: {to_lang}"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Create a new translation run
        translation_run = TranslationRun.objects.create(
            project_id=file_instance.project_id,
            service_id=file_instance.service_id,
            from_language=from_lang,
            to_language=to_lang,
            status="Processing",
            client_name=user.username if user and user.username else user.email
        )

        # ✅ Start translation asynchronously
        translate_document_task.delay(file_id, from_lang, to_lang)

        response_data = {
            "translation_run_id": str(translation_run.id),
            "file_id": str(file_instance.id),
            "status": "Processing"
        }

        return Response(response_data, status=status.HTTP_202_ACCEPTED)


### **🔹 Check Translation Status**
class CheckTranslationStatusAPIView(APIView):
    """
    Check the translation status using `translation_run_id`.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Check the status of a document translation using `translation_run_id`.",
        tags=["Translation Status"],
        manual_parameters=[client_id_param, client_secret_param, translation_run_id_param],
    )
    def get(self, request):
        translation_run_id = request.query_params.get("translation_run_id")

        if not translation_run_id:
            return Response({"error": "Missing `translation_run_id` parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Fetch translation status asynchronously
        result = check_translation_status_task.delay(translation_run_id).get()

        return Response(result, status=status.HTTP_200_OK if result["status"] == "Completed" else status.HTTP_202_ACCEPTED)


### **🔹 Download Translated File**
class DownloadTranslatedFileAPIView(APIView):
    """
    Download the translated file.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Download a translated document by providing the `file_id`.",
        tags=["Translation File Download"],
        manual_parameters=[client_id_param, client_secret_param, file_id_param],
    )
    def get(self, request):
        file_id = request.query_params.get("file_id")

        if not file_id:
            return Response({"error": "Missing `file_id` parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Fetch translated file path asynchronously
        result = download_translated_file_task.delay(file_id).get()

        if "error" in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        translated_filepath = result["translated_filepath"]

        if not os.path.exists(translated_filepath):
            return Response({"error": "Translated file not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {"file_id": file_id, "translated_filepath": translated_filepath, "status": "Ready for download"},
            status=status.HTTP_200_OK
        )


### **🔹 Handle Translation File Download View (Fix Swagger Errors)**
class TranslationFileDownloadView(generics.RetrieveAPIView):
    queryset = TranslationFile.objects.all()
    serializer_class = TranslationFileSerializer
    permission_classes = [AllowAny]  # ✅ Ensure API can be accessed

    @swagger_auto_schema(auto_schema=None)  # ✅ Prevent Swagger from generating schema errors
    def get(self, request, *args, **kwargs):
        if getattr(self, 'swagger_fake_view', False):
            return None  # ✅ Short-circuit schema generation for Swagger
        return super().get(request, *args, **kwargs)


