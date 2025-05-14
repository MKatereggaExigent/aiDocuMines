from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
import uuid
from datetime import datetime
from .models import Run, File, Storage, EndpointResponseTable, Metadata
from .tasks import process_metadata
from django.shortcuts import get_object_or_404
from oauth2_provider.models import Application
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from .utils import save_uploaded_file
from django.http import FileResponse
import logging
from django.db.utils import IntegrityError
from django.http import JsonResponse

from core.models import File
from grid_documents_interrogation.models import Topic
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from document_operations.models import Folder, FileFolderLink
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# ✅ Define Swagger parameters
client_id_param = openapi.Parameter(
    "X-Client-ID", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True, description="Client ID provided at signup"
)
project_id_param = openapi.Parameter(
    "project_id", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description="Project ID"
)
service_id_param = openapi.Parameter(
    "service_id", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description="Service ID"
)
file_param = openapi.Parameter(
    "file", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description="File(s) to upload"
)
file_id_param = openapi.Parameter(
    "file_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Unique File ID"
)


def get_user_from_client_id(client_id):
    """Retrieve the User associated with a given client_id from OAuth2 Application."""
    try:
        application = Application.objects.get(client_id=client_id)
        return application.user
    except Application.DoesNotExist:
        return None

def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class FileUploadView(APIView):
    """
    Upload files securely using OAuth2 authentication.
    """
    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Upload multiple files securely using OAuth2 authentication. Run ID is generated automatically.",
        tags=["File Upload"],
        manual_parameters=[client_id_param, project_id_param, service_id_param, file_param],
        responses={201: "Upload Successful", 400: "Bad Request", 403: "Forbidden"},
    )
    def post(self, request, *args, **kwargs):
        client_id = request.headers.get("X-Client-ID")
        access_token_string = request.headers.get("Authorization", "").split("Bearer ")[-1]

        # ✅ Enforce OAuth2 Authentication
        if not access_token_string:
            return Response({"error": "Authorization token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_user_from_client_id(client_id)
        if not user:
            return Response({"error": "Invalid client ID"}, status=status.HTTP_401_UNAUTHORIZED)

        project_id = request.data.get("project_id")
        service_id = request.data.get("service_id")
        files = request.FILES.getlist("file")

        if not all([client_id, project_id, service_id]) or not files:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(user.id)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        run_id = str(uuid.uuid4())  # ✅ Generated Internally

        # ✅ Create Run instance
        run = Run.objects.create(run_id=run_id, user=user, status="Pending")

        file_data = []
        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads", user_id, timestamp, client_id, project_id, service_id, run_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            try:
                temp_dir = os.path.join(upload_dir, "temp")
                os.makedirs(temp_dir, exist_ok=True)
            
                # Temporarily save the file to compute MD5 only
                temp_details = save_uploaded_file(file, temp_dir)
            
                # ✅ Check for existing file BEFORE permanently saving
                existing_file = File.objects.filter(md5_hash=temp_details["md5_hash"]).first()
            
                if existing_file:
                    if existing_file.user == user:
                        logger.info(f"📎 Duplicate file by same user: {temp_details['filename']}")
                        # Clean up the temporary file
                        os.remove(temp_details["file_path"])
                        return Response({
                            "message": "Duplicate file already exists under your account.",
                            "file_id": existing_file.id,
                            "filename": temp_details["filename"],
                            "md5_hash": existing_file.md5_hash,
                            "project_id": existing_file.project_id,
                            "service_id": existing_file.service_id,
                            "filepath": existing_file.filepath,
                        }, status=status.HTTP_200_OK)
                    else:
                        logger.info(f"🔗 Sharing existing file {existing_file.id} with new user {user.id}")
                        os.remove(temp_details["file_path"])  # Clean up the temporary file
            
                        # Use existing file but link to this user/project/service
                        storage = existing_file.storage
                        file_instance = File.objects.create(
                            run=run,
                            storage=storage,
                            filename=existing_file.filename,
                            filepath=existing_file.filepath,
                            file_size=existing_file.file_size,
                            file_type=existing_file.file_type,
                            md5_hash=existing_file.md5_hash,
                            user=user,
                            project_id=project_id,
                            service_id=service_id,
                        )
            
                        # Link to folder
                        folder, _ = Folder.objects.get_or_create(
                            name=project_id,
                            user=user,
                            project_id=project_id,
                            service_id=service_id,
                            defaults={"created_at": timezone.now()}
                        )
                        FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)
            
                        return Response({
                            "message": "Duplicate file reused from another user and linked to your account.",
                            "file_id": file_instance.id,
                            "filename": file_instance.filename,
                            "md5_hash": file_instance.md5_hash,
                            "project_id": project_id,
                            "service_id": service_id,
                            "filepath": file_instance.filepath,
                        }, status=status.HTTP_201_CREATED)
            
                # ✅ No duplicate: save permanently
                final_path = os.path.join(upload_dir, temp_details["filename"])
                os.rename(temp_details["file_path"], final_path)
                temp_details["file_path"] = final_path
            
                # Save storage & DB entry
                #storage = Storage.objects.create(user=user, run=run, upload_storage_location=final_path)
                storage = Storage.objects.create(user=user, content_type=ContentType.objects.get_for_model(run.__class__), upload_storage_location=final_path)
    
                # ✅ No duplicate: create a preliminary File instance to get file_id
                #storage = Storage.objects.create(user=user, run=run)  # Temp storage, we'll update upload path after
                storage = Storage.objects.create(user=user, content_type=ContentType.objects.get_for_model(run.__class__))  # Temp storage, we'll update upload path after

                file_instance = File.objects.create(
                    run=run,
                    storage=storage,
                    filename=temp_details["filename"],
                    filepath="",  # temp placeholder
                    file_size=temp_details["file_size"],
                    file_type=temp_details["file_type"],
                    md5_hash=temp_details["md5_hash"],
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                )

                # ✅ Now we have the file_id; compute final path
                final_upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads", user_id, timestamp, client_id, project_id, service_id, run_id, str(file_instance.id))
                os.makedirs(final_upload_dir, exist_ok=True)

                # Move file to final location
                final_path = os.path.join(final_upload_dir, temp_details["filename"])
                os.rename(temp_details["file_path"], final_path)
                temp_details["file_path"] = final_path

                # ✅ Update File and Storage with correct filepath
                file_instance.filepath = final_path
                file_instance.save()

                storage.upload_storage_location = final_path
                storage.save()

                # Record file info for response
                file_data.append({
                    "file_id": file_instance.id,
                    "filename": temp_details["filename"],
                    "file_size": temp_details["file_size"],
                    "mime_type": temp_details["file_type"],
                    "message": "File successfully uploaded.",
                })

                # ✅ Link to folder
                folder, _ = Folder.objects.get_or_create(
                    name=project_id,
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                    defaults={"created_at": timezone.now()}
                )
                FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)


                '''
                file_instance = File.objects.create(
                    run=run,
                    storage=storage,
                    filename=temp_details["filename"],
                    filepath=final_path,
                    file_size=temp_details["file_size"],
                    file_type=temp_details["file_type"],
                    md5_hash=temp_details["md5_hash"],
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                )
            
                file_data.append({
                    "file_id": file_instance.id,
                    "filename": temp_details["filename"],
                    "file_size": temp_details["file_size"],
                    "mime_type": temp_details["file_type"],
                    "message": "File successfully uploaded.",
                })
            
                folder, _ = Folder.objects.get_or_create(
                    name=project_id,
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                    defaults={"created_at": timezone.now()}
                )
                FileFolderLink.objects.get_or_create(file=file_instance, folder=folder) 
                '''

            except IntegrityError as e:
                if 'core_file_md5_hash_key' in str(e):
                    existing_file = File.objects.filter(md5_hash=file_details["md5_hash"]).first()
            
                    if existing_file:
                        if existing_file.user == user:
                            # ✅ Duplicate by same user – just return existing info
                            logger.info(f"📎 Duplicate file by same user: {file_details['filename']}")
                            return Response({
                                "message": "Duplicate file already exists under your account.",
                                "file_id": existing_file.id,
                                "filename": file_details["filename"],
                                "md5_hash": existing_file.md5_hash,
                                "project_id": existing_file.project_id,
                                "service_id": existing_file.service_id,
                                "filepath": existing_file.filepath,
                            }, status=status.HTTP_200_OK)
                        else:
                            # ✅ Duplicate file but uploaded by another user – link to current user
                            logger.info(f"🔗 Sharing existing file {existing_file.id} with new user {user.id}")
                            
                            # Link the file to the current user (e.g. via folder or permission)
                            file_instance = File.objects.create(
                                run=run,
                                storage=existing_file.storage,
                                filename=existing_file.filename,
                                filepath=existing_file.filepath,
                                file_size=existing_file.file_size,
                                file_type=existing_file.file_type,
                                md5_hash=existing_file.md5_hash,
                                user=user,
                                project_id=project_id,
                                service_id=service_id,
                            )
            
                            # Link to folder
                            folder, _ = Folder.objects.get_or_create(
                                name=project_id,
                                user=user,
                                project_id=project_id,
                                service_id=service_id,
                                defaults={"created_at": timezone.now()}
                            )
                            FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)
                            
                            # Clean up temp file and run_id directory if unused
                            import shutil  # make sure it's imported at the top

                            # Clean up the temporary file
                            try:
                                os.remove(temp_details["file_path"])
                                
                                # ✅ Delete empty /temp directory
                                temp_dir = os.path.dirname(temp_details["file_path"])
                                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                                    os.rmdir(temp_dir)
                                    logger.info(f"🧹 Cleaned up empty temp folder: {temp_dir}")

                                # ✅ Delete run_id directory if empty or only had temp
                                run_dir = os.path.dirname(temp_dir)
                                contents = os.listdir(run_dir)
                                if not contents or (contents == ["temp"] and not os.listdir(temp_dir)):
                                    shutil.rmtree(run_dir)
                                    logger.info(f"🧹 Cleaned up unused run directory: {run_dir}")
                            except Exception as cleanup_err:
                                logger.warning(f"⚠️ Cleanup failed: {cleanup_err}")

                                    
                            except Exception as cleanup_err:
                                logger.warning(f"⚠️ Cleanup failed: {cleanup_err}")
            
                            return Response({
                                "message": "Duplicate file reused from another user and linked to your account.",
                                "file_id": file_instance.id,
                                "filename": file_instance.filename,
                                "md5_hash": file_instance.md5_hash,
                                "project_id": project_id,
                                "service_id": service_id,
                                "filepath": file_instance.filepath,
                            }, status=status.HTTP_201_CREATED)
                            
                    else:
                        logger.error(f"❌ Integrity error but no matching file found for hash: {file_details['md5_hash']}")
                        return Response({"error": "Duplicate hash but no matching file record found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    logger.error(f"❌ Database error during file upload: {e}")
                    return Response({"error": "An unexpected database error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "message": "File upload received, processing in background.",
                "run_id": run_id,
                "files": file_data,
            },
            status=status.HTTP_201_CREATED,
        )


class UniversalTaskStatusView(APIView):
    """
    Fetch the latest status for a given run_id from EndpointResponseTable.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Retrieve the status of an asynchronous task using run_id.",
        tags=["Task Status"],
        manual_parameters=[
            client_id_param,
            openapi.Parameter("run_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Unique Run ID to track processing"),
        ],
        responses={200: "Success", 404: "Not Found"},
    )
    def get(self, request):
        """
        Retrieve the task status using run_id.
        """
        client_id = request.headers.get("X-Client-ID")
        access_token_string = request.headers.get("Authorization", "").split("Bearer ")[-1]
        run_id = request.query_params.get("run_id")

        # ✅ Enforce OAuth2 Authentication
        if not access_token_string:
            return Response({"error": "Authorization token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_user_from_client_id(client_id)
        if not user:
            return Response({"error": "Invalid client ID"}, status=status.HTTP_401_UNAUTHORIZED)

        if not run_id:
            return Response({"error": "Missing run_id parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Fetch task status
        response_entry = EndpointResponseTable.objects.filter(run__run_id=run_id).order_by("-created_at").first()

        if not response_entry:
            return Response({"error": "No status found for the provided run_id."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "run_id": run_id,
                "status": response_entry.status,
                "endpoint": response_entry.endpoint_name,
                "response_data": response_entry.response_data,
            },
            status=status.HTTP_200_OK if response_entry.status == "Completed" else status.HTTP_202_ACCEPTED,
        )

@method_decorator(csrf_exempt, name="dispatch")
class MetadataView(APIView):
    """
    ✅ Triggers metadata extraction for a given file.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Trigger metadata extraction for a specific file.",
        tags=["Core Application: Metadata Extraction"],
        manual_parameters=[client_id_param, file_id_param],
        responses={202: "Processing started", 400: "Bad Request", 404: "Not Found"},
    )
    def post(self, request):
        client_id = request.headers.get("X-Client-ID")
        file_id = request.query_params.get("file_id")

        # ✅ Fetch file instance
        file_instance = get_object_or_404(File, id=file_id)

        # ✅ Generate a new run_id for the metadata extraction process
        run_id = str(uuid.uuid4())
        run = Run.objects.create(run_id=run_id, user=file_instance.user, status="Processing")

        # ✅ Trigger metadata extraction task
        from .tasks import process_metadata
        process_metadata.delay(file_instance.id, run.run_id)

        return Response(
            {
                "message": "Metadata extraction started.",
                "run_id": run_id,
                "file_id": file_instance.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class FileDownloadView(APIView):
    """
    ✅ Download a file using file_id
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Download a file using file_id.",
        tags=["Core Application: File Download"],
        manual_parameters=[client_id_param, file_id_param],
        responses={200: "Success", 404: "File Not Found"},
    )
    def get(self, request):
        client_id = request.headers.get("X-Client-ID")
        file_id = request.query_params.get("file_id")

        # ✅ Fetch file instance
        file_instance = get_object_or_404(File, id=file_id)

        # ✅ Check if file exists
        if not os.path.exists(file_instance.filepath):
            return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Return FileResponse for download
        return FileResponse(open(file_instance.filepath, "rb"), as_attachment=True, filename=file_instance.filename)



@method_decorator(csrf_exempt, name="dispatch")
class BulkFolderUploadView(APIView):
    """
    Upload a folder of documents (recursive) and preserve subdirectory structure.
    """
    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Upload a folder with multiple documents. Subdirectory structure is preserved.",
        tags=["Folder Upload"],
        manual_parameters=[client_id_param, project_id_param, service_id_param, file_param],
        responses={201: "Bulk Upload Successful", 400: "Bad Request", 403: "Forbidden"},
    )
    def post(self, request):
        client_id = request.headers.get("X-Client-ID")
        access_token_string = request.headers.get("Authorization", "").split("Bearer ")[-1]

        if not access_token_string:
            return Response({"error": "Authorization token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_user_from_client_id(client_id)
        if not user:
            return Response({"error": "Invalid client ID"}, status=status.HTTP_401_UNAUTHORIZED)

        project_id = request.data.get("project_id")
        service_id = request.data.get("service_id")
        files = request.FILES.getlist("file")

        if not all([client_id, project_id, service_id]) or not files:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(user.id)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        run_id = str(uuid.uuid4())
        run = Run.objects.create(run_id=run_id, user=user, status="Pending")

        upload_dir_base = os.path.join(settings.MEDIA_ROOT, "uploads", user_id, timestamp, client_id, project_id, service_id, run_id)
        os.makedirs(upload_dir_base, exist_ok=True)

        uploaded_files_data = []

        for f in files:
            relative_path = f.name  # `webkitRelativePath` from frontend
            target_path = os.path.join(upload_dir_base, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            file_details = save_uploaded_file(f, os.path.dirname(target_path), custom_filename=os.path.basename(target_path))

            try:
                storage = Storage.objects.create(user=user, content_type=ContentType.objects.get_for_model(run.__class__), upload_storage_location=file_details["file_path"])

                file_instance = File.objects.create(
                    run=run,
                    storage=storage,
                    filename=file_details["filename"],
                    filepath=file_details["file_path"],
                    file_size=file_details["file_size"],
                    file_type=file_details["file_type"],
                    md5_hash=file_details["md5_hash"],
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                )

                uploaded_files_data.append({
                    "file_id": file_instance.id,
                    "filename": file_details["filename"],
                    "relative_path": relative_path,
                    "file_size": file_details["file_size"],
                    "mime_type": file_details["file_type"],
                })

                # 🔹 Create/get folder for project-service-user
                folder, _ = Folder.objects.get_or_create(
                    name=project_id,
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                    defaults={"created_at": timezone.now()}
                    )

                # 🔹 Link file to folder if not already linked
                if not FileFolderLink.objects.filter(file=file_instance).exists():
                    FileFolderLink.objects.create(file=file_instance, folder=folder)


            except IntegrityError as e:
                if 'core_file_md5_hash_key' in str(e):
                    existing = File.objects.filter(md5_hash=file_details["md5_hash"]).first()
                    return Response({
                        "error": "Duplicate file detected.",
                        "filename": file_details["filename"],
                        "existing_file_id": existing.id if existing else None,
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Folder upload successful.",
            "run_id": run_id,
            "files": uploaded_files_data,
        }, status=status.HTTP_201_CREATED)



class AssociateTopicToFileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, file_id):
        topic_id = request.data.get("topic_id")
        if not topic_id:
            return Response({"error": "Missing topic_id"}, status=status.HTTP_400_BAD_REQUEST)

        file = get_object_or_404(File, pk=file_id, user=request.user)
        topic = get_object_or_404(Topic, pk=topic_id, user=request.user)

        file.topic = topic
        file.save()

        return Response({"message": f"File {file.id} successfully linked to topic {topic.id}"}, status=status.HTTP_200_OK)
