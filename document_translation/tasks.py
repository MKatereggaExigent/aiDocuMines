import os
import logging
import uuid
import time
from celery import shared_task
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from core.models import File
from document_translation.models import TranslationRun, TranslationFile
from document_translation.utils import TranslationService, AzureBlobService

# ✅ Initialize Services
logger = logging.getLogger(__name__)
translation_service = TranslationService()
azure_service = AzureBlobService()


@shared_task
def translate_document_task(file_id, from_language, to_language):
    """
    Celery task to translate a document (outputs translated file).
    """
    logger.info(f"🔄 Starting translation for file_id: {file_id}, from {from_language} to {to_language}")

    # ✅ Fetch file from database
    file_entry = get_object_or_404(File, id=file_id)

    if not os.path.exists(file_entry.filepath):
        logger.error(f"❌ File not found: {file_entry.filepath}")
        return {"error": "File not found", "file_id": file_id}

    # ✅ Check if the translation already exists
    existing_translation = TranslationFile.objects.filter(
        original_file=file_entry, run__to_language=to_language
    ).first()

    if existing_translation:
        logger.info(f"⚠️ Skipping duplicate translation: {existing_translation.translated_filepath}")
        return {
            "translation_run_id": str(existing_translation.run.id),
            "file_id": file_id,
            "translated_filepath": existing_translation.translated_filepath,
            "status": "Completed",
        }

    # ✅ Create structured translation directory (same as OCR)
    translation_dir = os.path.join(os.path.dirname(file_entry.filepath), "translations", to_language)
    os.makedirs(translation_dir, exist_ok=True)

    # ✅ Create a `TranslationRun` instance
    translation_run = TranslationRun.objects.create(
        project_id=file_entry.project_id,
        service_id=file_entry.service_id,
        client_name=file_entry.user.username if file_entry.user and file_entry.user.username else file_entry.user.email,
        status="Pending",  # ✅ Set to "Pending" initially
        from_language=from_language,
        to_language=to_language,
    )

    # ✅ Define unique Azure containers for this translation
    source_container = f"translation-source-{uuid.uuid4()}"
    target_container = f"translation-target-{uuid.uuid4()}"

    try:
        # ✅ Ensure Azure Containers Exist
        azure_service.ensure_container_exists(source_container)
        azure_service.ensure_container_exists(target_container)

        # ✅ Upload file if it does not exist in Azure Storage
        azure_service.upload_file_if_not_exists(source_container, file_entry.filepath)

        # ✅ Initiate translation process
        translation_result = translation_service.translate_file(
            file_entry.id, translation_run.id, from_language, to_language
        )

        # ✅ Validate translation result
        translated_filepath = translation_result.get("translated_file")

        if not translated_filepath or not os.path.exists(translated_filepath):
            logger.error("❌ Translation completed, but no translated file was found.")
            raise ValueError("Translation process completed, but no translated file was found.")

        # ✅ Update `TranslationRun` to "Completed"
        translation_run.status = "Completed"
        translation_run.save()

        # ✅ Store translated file in `TranslationFile` model
        with transaction.atomic():
            TranslationFile.objects.create(
                original_file=file_entry,
                run=translation_run,
                translated_filepath=translated_filepath,
                status="Completed",
                created_at=now(),
                updated_at=now(),
            )

        logger.info(f"✅ Translation completed for file_id: {file_id}, translated file: {translated_filepath}")

        return {
            "translation_run_id": str(translation_run.id),
            "file_id": file_id,
            "translated_filepath": translated_filepath,
            "status": "Completed",
        }

    except Exception as e:
        logger.error(f"❌ Translation failed: {e}")
        translation_run.status = "Failed"
        translation_run.error_message = str(e)
        translation_run.save()
        return {"error": str(e), "file_id": file_id}

    finally:
        # ✅ Ensure containers are deleted to clean up storage
        azure_service.delete_container(source_container)
        azure_service.delete_container(target_container)


@shared_task
def check_translation_status_task(translation_run_id):
    """
    Celery task to check the status of a translation process.
    """
    logger.info(f"🔄 Checking status for translation_run_id: {translation_run_id}")

    # ✅ Fetch the translation run instance
    translation_run = get_object_or_404(TranslationRun, id=translation_run_id)

    return {
        "translation_run_id": translation_run_id,
        "status": translation_run.status,
        "from_language": translation_run.from_language,
        "to_language": translation_run.to_language,
    }


@shared_task
def download_translated_file_task(file_id):
    """
    Celery task to download the translated document.
    """
    logger.info(f"🔄 Downloading translated file for file_id: {file_id}")

    # ✅ Fetch translated file entry
    translated_file = get_object_or_404(TranslationFile, original_file_id=file_id)
    target_container = f"translation-target-{translated_file.run.to_language}"

    # ✅ Define structured output directory (matching `document_ocr`)
    translated_file_path = os.path.join(
        os.path.dirname(translated_file.original_file.filepath),
        "translations",
        f"translated-{uuid.uuid4()}.pdf"
    )
    os.makedirs(os.path.dirname(translated_file_path), exist_ok=True)

    # ✅ Download translated file from Azure
    azure_service.download_files(target_container, os.path.dirname(translated_file_path))

    # ✅ Verify translation file exists
    if not os.path.exists(translated_file_path):
        logger.error(f"❌ Translated file not found: {translated_file_path}")
        return {"error": "Translated file not found", "file_id": file_id}

    # ✅ Update `TranslationFile` model with correct path
    with transaction.atomic():
        translated_file.translated_filepath = translated_file_path
        translated_file.status = "Ready for download"
        translated_file.save()

    logger.info(f"✅ Translated file ready for download: {translated_file.translated_filepath}")

    return {
        "file_id": file_id,
        "translated_filepath": translated_file.translated_filepath,
        "status": "Ready for download",
    }
