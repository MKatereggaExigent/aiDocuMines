from celery import shared_task
import os
import logging
from django.conf import settings
from oauth2_provider.models import Application
from django.utils.timezone import make_aware
from datetime import datetime
import asyncio

from pytz import timezone, UTC
from celery import group
from .models import File, Metadata, Storage, Run, EndpointResponseTable
from .utils import save_uploaded_file, extract_metadata, calculate_md5, convert_pdf_date, str_to_bool
from .serializers import MetadataSerializer


logger = logging.getLogger(__name__)

from .utils import extract_metadata


@shared_task(bind=True)
def process_metadata(self, file_id, run_id):
    """Celery task to extract metadata asynchronously and store in DB."""
    try:
        file_instance = File.objects.get(id=file_id)
        run = Run.objects.get(run_id=run_id)

        logger.warning(f"🔍 **Processing metadata for file_id: {file_id}, run_id: {run_id}**")

        # ✅ Extract metadata
        metadata_data = extract_metadata(file_instance)

        if not metadata_data:
            logger.error(f"❌ Metadata extraction failed for file_id {file_id}")
            return {"error": "Metadata extraction failed."}

        logger.info(f"✅ Extracted metadata data: {metadata_data}")

        # 🔐 Normalize all boolean fields
        boolean_fields = [
            "is_encrypted", "encrypted", "optimized", "tagged",
            "userproperties", "suspects", "custom_metadata", "metadata_stream"
        ]
        for key in boolean_fields:
            if key in metadata_data:
                metadata_data[key] = str_to_bool(metadata_data[key])

        
        # ✅ Convert Dates to Django `datetime` format (Ensures Correct Storage)
        #def parse_date(date_str):
        #    """Converts a string date into a Django-aware datetime object."""
        #    if not date_str:
        #        return None
        #    try:
        #        dt = datetime.fromisoformat(date_str)  # Convert from ISO 8601
        #        return make_aware(dt)  # Ensure it's timezone-aware
        #    except ValueError:
        #        logger.warning(f"⚠️ Failed to parse date: {date_str}")
        #        return None
        


        def parse_date(date_str):
            """Converts a string date into a Django-aware datetime object."""
            if not date_str:
                return None
            try:
                # Primary: ISO format
                dt = datetime.fromisoformat(date_str)
                return make_aware(dt)
            except ValueError:
                pass

            try:
                # Fallback 1: "Fri Jan 24 03:38:03 2025 CST"
                dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %Z")
                return dt.replace(tzinfo=UTC)  # or use pytz.timezone("US/Central") if you want CST
            except ValueError:
                pass

            try:
                # Fallback 2: "/creationdate": "D:20250124093803+00'00'"
                if date_str.startswith("D:"):
                    cleaned = date_str[2:].split("+")[0]
                    dt = datetime.strptime(cleaned, "%Y%m%d%H%M%S")
                    return make_aware(dt)
            except Exception:
                pass

            logger.warning(f"⚠️ Failed to parse date: {date_str}")
            return None



        creationdate = parse_date(metadata_data.get("creationdate", None))
        moddate = parse_date(metadata_data.get("moddate", None))

        # ✅ Ensure Metadata is saved correctly
        metadata, created = Metadata.objects.update_or_create(
            file=file_instance,
            defaults = {
                "storage": file_instance.storage,  # ✅ Link Storage
                "file_size": metadata_data.get("file_size", None),
                "format": metadata_data.get("format", None),
                "md5_hash": metadata_data.get("md5_hash", None),
                "title": metadata_data.get("title", None),
                "author": metadata_data.get("author", None),
                "subject": metadata_data.get("subject", None),
                "keywords": metadata_data.get("keywords", None),
                "creator": metadata_data.get("creator", None),
                "producer": metadata_data.get("producer", None),
                "creationdate": creationdate, # metadata_data.get("creationdate", None),  # Corrected from creation_date
                "moddate": moddate, # metadata_data.get("moddate", None),  # Corrected from modDate
                "trapped": metadata_data.get("trapped", None),
                "encryption": metadata_data.get("encryption", None),
                "page_count": metadata_data.get("page_count", 0),
                "is_encrypted": metadata_data.get("is_encrypted", False),
                "fonts": metadata_data.get("fonts", None),
                "page_rotation": metadata_data.get("page_rotation", 0),
                "pdfminer_info": metadata_data.get("pdfminer_info", None),
                "metadata_stream": metadata_data.get("metadata_stream", None),
                "tagged": metadata_data.get("tagged", None),
                "userproperties": metadata_data.get("userproperties", None),  # Corrected from user_properties
                "suspects": metadata_data.get("suspects", None),
                "form": metadata_data.get("form", None),
                "javascript": metadata_data.get("javascript", None),
                "pages": metadata_data.get("pages", None),
                "encrypted": metadata_data.get("encrypted", False),
                "page_size": metadata_data.get("page_size", None),
                "optimized": metadata_data.get("optimized", False),
                "pdf_version": metadata_data.get("pdf_version", None),
                "word_count": metadata_data.get("word_count", 0),
            }
        )
        logger.info(f"✅ Metadata saved: {metadata}")



        # ✅ Save task result in EndpointResponseTable
        EndpointResponseTable.objects.update_or_create(
            run=run,
            client=file_instance.user,
            endpoint_name="MetadataView",
            defaults={
                "status": "Completed",
                "response_data": {
                    "metadata_id": metadata.metadata_id,
                    "file_id": file_instance.id,
                    "filename": file_instance.filename,
                    "md5_hash": metadata.md5_hash,
                    "format": metadata.format,
                    "pdf_version": metadata.pdf_version,
                    "page_count": metadata.page_count,
                    "fonts": metadata.fonts,
                    "created_at": str(metadata.created_at),
                },
            },
        )


        # ✅ Update run status
        run.status = "Completed"
        run.save(update_fields=["status"])

        return {
            "message": "Metadata extraction completed.",
            "metadata_id": metadata.metadata_id,
        }

    except File.DoesNotExist:
        logger.error("❌ File does not exist.")
        return {"error": "File does not exist."}
    except Run.DoesNotExist:
        logger.error(f"❌ Run ID {run_id} does not exist.")
        return {"error": f"Run ID {run_id} does not exist."}
    except Exception as e:
        logger.error(f"❌ Metadata extraction failed: {str(e)}")
        return {"error": str(e)}




@shared_task(bind=True)
def process_bulk_metadata(self, run_id):
    """
    Process metadata for all files belonging to the given run_id in parallel.
    Aggregates individual tasks for Celery to process concurrently.
    """
    try:
        run = Run.objects.get(run_id=run_id)
        files = File.objects.filter(run=run)

        if not files.exists():
            logger.warning(f"⚠️ No files found for run_id: {run_id}")
            return {"warning": "No files found for this run_id."}

        logger.info(f"🚀 Triggering bulk metadata extraction for run_id: {run_id} with {files.count()} files")

        # 🔁 Launch a group of tasks concurrently
        metadata_tasks = group(process_metadata.s(file.id, run_id) for file in files)
        result = metadata_tasks.apply_async()

        return {"message": "Bulk metadata extraction triggered.", "task_ids": result.id}

    except Run.DoesNotExist:
        logger.error(f"❌ Run ID {run_id} not found for bulk metadata processing.")
        return {"error": f"Run ID {run_id} not found."}
    except Exception as e:
        logger.error(f"❌ Bulk metadata processing failed: {str(e)}")
        return {"error": str(e)}


@shared_task
def process_file(file_id):
    """
    Celery task to process a file and update the response table.
    """
    try:
        file_instance = File.objects.get(id=file_id)
        run = file_instance.run

        # ✅ Get client_id from OAuth2 Application model
        application = Application.objects.get(user=run.user)
        client_id = application.client_id  # ✅ Correct way to get client_id

        # ✅ Step 1: Compute MD5 Hash
        file_hash = asyncio.run(calculate_md5(file_instance.filepath))

        # ✅ Step 2: Update File Instance with Hash
        file_instance.md5_hash = file_hash
        file_instance.save(update_fields=["md5_hash"])

        # ✅ Step 3: Store or update response in EndpointResponseTable
        endpoint_response, created = EndpointResponseTable.objects.update_or_create(
            run=run,
            endpoint_name="FileUploadView",
            defaults={
                "status": "Completed",
                "response_data": {
                    "client_id": client_id,
                    "project_id": file_instance.project_id,
                    "service_id": file_instance.service_id,
                    "user": file_instance.user.username,
                    "files": [
                        {
                            "file_id": file_instance.id,
                            "filename": file_instance.filename,
                            "filepath": file_instance.filepath,
                            "md5_hash": file_hash,
                        }
                    ]
                }
            }
        )

        logger.info(f"✅ File processing completed for file_id: {file_id}")

    except Exception as e:
        # ✅ Handle failures and store error message
        endpoint_response, created = EndpointResponseTable.objects.update_or_create(
            run=run,
            endpoint_name="FileUploadView",
            defaults={
                "status": "Failed",
                "response_data": {"error": str(e)}
            }
        )
        logger.error(f"❌ File processing failed for file_id: {file_id} - Error: {str(e)}")





@shared_task
def extract_document_text_task(file_id):
    from core.utils import extract_document_text

    try:
        file_obj = File.objects.get(id=file_id)
    except File.DoesNotExist:
        return

    text = extract_document_text(file_obj.filepath, file_obj.file_type)
    file_obj.content = text
    file_obj.save(update_fields=["content"])



# @shared_task
# async def async_process_upload(uploaded_file, user_id, project_id, service_id, run_id):
    # """
    # Asynchronous file upload processing task.
    # """
    # try:
        # file_details = await save_uploaded_file(uploaded_file, user_id, project_id, service_id, run_id)
# 
        # ✅ Create File instance in DB
        # file_instance = File.objects.create(
            # filename=file_details["filename"],
            # filepath=file_details["file_path"],
            # file_size=file_details["file_size"],
            # file_type=file_details["file_type"],
            # md5_hash=file_details["md5_hash"],
            # run=Run.objects.get(run_id=run_id),
            # user_id=user_id,
            # client_id=user_id,  # Assuming client_id is same as user_id
            # project_id=project_id,
            # service_id=service_id,
        # )
# 
        # logger.info(f"✅ File upload completed: {file_instance.filename} - ID: {file_instance.id}")
# 
        # return {"message": "File uploaded successfully", "file_id": file_instance.id}
# 
    # except Exception as e:
        # logger.error(f"❌ File upload failed - Error: {str(e)}")
        # return {"error": f"File upload failed: {str(e)}"}
# 
