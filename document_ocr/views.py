from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from oauth2_provider.models import Application
from core.models import File
from document_ocr.models import OCRRun, OCRFile
from document_ocr.tasks import process_ocr
import os
import logging
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid
from glob import glob

logger = logging.getLogger(__name__)

User = get_user_model()

# Define Swagger parameters
client_id_param = openapi.Parameter(
    "X-Client-ID", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True, description="Client ID provided at signup"
)
client_secret_param = openapi.Parameter(
    "X-Client-Secret", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True, description="Client Secret for authentication"
)
file_id_param = openapi.Parameter(
    "file_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Unique File ID"
)
project_id_param = openapi.Parameter(
    "project_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Project ID associated with the file"
)
service_id_param = openapi.Parameter(
    "service_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Service ID defining the processing pipeline"
)
ocr_option_param = openapi.Parameter(
    "ocr_option", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True,
    description="OCR Processing type: 'Basic-ocr' or 'Advanced-ocr'"
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


class SubmitOCRAPIView(APIView):
    """
    Submit a file for OCR processing.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Submit a file for OCR processing.",
        tags=["OCR Processing"],
        manual_parameters=[
            client_id_param, client_secret_param, file_id_param, project_id_param, service_id_param, ocr_option_param
        ],
    )
    def post(self, request):
        file_id = request.query_params.get("file_id")
        ocr_option = request.query_params.get("ocr_option")

        # Validate file
        file_obj = get_object_or_404(File, id=file_id)
        if not os.path.exists(file_obj.filepath):
            return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate OCR option
        if ocr_option not in ["Basic-ocr", "Advanced-ocr"]:
            return Response({"error": "Invalid OCR option."}, status=status.HTTP_400_BAD_REQUEST)

        # Define OCR directory path based on the ocr_option
        ocr_dir = os.path.join(os.path.dirname(file_obj.filepath), "ocr", ocr_option.lower())

        # Check if the OCR directory exists and is **not empty**
        if os.path.exists(ocr_dir) and any(os.scandir(ocr_dir)):  # Skip OCR if already processed
            logger.info(f"⚠️ OCR skipped: Existing processed files found in {ocr_dir}")

            # Retrieve the run_id from existing OCR run for this file
            ocr_run = OCRRun.objects.filter(project_id=file_obj.project_id, service_id=file_obj.service_id, client_name=file_obj.user.username).first()
            return Response({
                "ocr_run_id": str(ocr_run.id) if ocr_run else "N/A",
                "status": "Processing",
                "message": "File has already been processed. Skipping OCR."
            }, status=status.HTTP_202_ACCEPTED)

        # Create OCRRun
        ocr_run = OCRRun.objects.create(
            project_id=file_obj.project_id,
            service_id=file_obj.service_id,
            client_name=file_obj.user.username if file_obj.user and file_obj.user.username else file_obj.user.email,
            status="Pending",
            ocr_option=ocr_option  # Storing the OCR option
        )

        # Start OCR task
        process_ocr.delay(ocr_run.id, file_id, ocr_option)

        return Response({
            "ocr_run_id": str(ocr_run.id),
            "status": "Processing"
        }, status=status.HTTP_202_ACCEPTED)


class CheckOCRStatusAPIView(APIView):
    """
    Check the OCR status using `ocr_run_id`.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Check the status of an OCR process using `ocr_run_id`.",
        tags=["OCR Status"],
        manual_parameters=[
            client_id_param, client_secret_param,
            openapi.Parameter("ocr_run_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True,
                              description="Unique `ocr_run_id` to track OCR processing."),
        ],
    )
    def get(self, request):
        client_id = request.headers.get("X-Client-ID")
        client_secret = request.headers.get("X-Client-Secret")
        ocr_run_id = request.query_params.get("ocr_run_id")

        if not all([client_id, client_secret, ocr_run_id]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_from_client_id(client_id)
        if not user:
            return Response({"error": "Invalid client ID"}, status=status.HTTP_401_UNAUTHORIZED)

        # Fetch `OCRRun`
        ocr_run = get_object_or_404(OCRRun, id=ocr_run_id)

        # Retrieve OCR file if completed
        ocr_file = OCRFile.objects.filter(run=ocr_run).first()
        ocr_filepath = ocr_file.ocr_filepath if ocr_file else None
        docx_filepath = ocr_file.docx_path if ocr_file else None
        raw_docx_filepath = ocr_file.raw_docx_path if ocr_file else None

        return Response(
            {
                "ocr_run_id": ocr_run_id,
                "file_id": ocr_file.original_file.id if ocr_file else None,
                "project_id": ocr_run.project_id,
                "service_id": ocr_run.service_id,
                "client_name": ocr_run.client_name,
                "ocr_option": ocr_run.ocr_option,  # Return OCR type
                "status": ocr_run.status,
                "ocr_filepath": ocr_filepath,
                "docx_filepath": docx_filepath,
                "raw_docx_filepath": raw_docx_filepath,
            },
            status=status.HTTP_200_OK if ocr_run.status == "Completed" else status.HTTP_202_ACCEPTED,
        )

