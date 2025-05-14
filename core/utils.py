import os
import logging
import mimetypes
from pathlib import Path
from django.conf import settings
import hashlib
from PyPDF2 import PdfReader
from docx import Document

import PyPDF2

import fitz  # PyMuPDF
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import subprocess
from datetime import datetime, timedelta

import dateutil.parser
from dateutil import parser as dateutil_parser

import zipfile
import xml.etree.ElementTree as ET

from unidecode import unidecode
import re

import hashlib
from core.models import File, Storage
from document_operations.models import Folder, FileFolderLink
from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# ✅ Allowed file types (MIME types)
ALLOWED_FILE_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "txt": "text/plain",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "gif": "image/gif",
}

# ✅ Max file size (100MB limit)
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024



def str_to_bool(value):
    """Converts various truthy/falsy string values to boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ["true", "yes", "1"]


def sanitize_filename(filename):
    """Sanitizes the filename by replacing special characters.

    Args:
        filename (str): The original filename.

    Returns:
        str: The sanitized filename.
    """
    # Replace German special characters with normal letters
    filename = unidecode(filename)

    # Replace all spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove all special characters except hyphens and underscores
    filename = re.sub(r"[^a-zA-Z0-9\-_.]", "", filename)

    return filename


def rename_files_in_folder(folder_path):
    """Renames all files in a folder and its subfolders by sanitizing filenames.

    Args:
        folder_path (str): The path of the folder.
    """
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            # Full path of the file
            full_file_path = os.path.join(root, filename)

            # Sanitize the filename
            sanitized_name = sanitize_filename(filename)

            # Full path of the new file name
            full_sanitized_path = os.path.join(root, sanitized_name)

            # Rename the file
            os.rename(full_file_path, full_sanitized_path)
            print(f"Renamed {full_file_path} to {full_sanitized_path}")


# def save_uploaded_file(uploaded_file, storage_path: str):
def save_uploaded_file(uploaded_file, storage_path: str, custom_filename=None):
    """
    Saves uploaded files synchronously.

    :param uploaded_file: File object from Django (InMemoryUploadedFile or TemporaryUploadedFile)
    :param storage_path: System location of uploaded files
    :return: File metadata dictionary
    """
    # ✅ Validate file size
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")

    # ✅ Validate file type
    file_name = uploaded_file.name  
    file_ext = file_name.split(".")[-1].lower()
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    if file_ext not in ALLOWED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {file_ext}")

    file_path = os.path.join(storage_path, file_name)

    # ✅ Save file in chunks
    chunk_size = 64 * 1024  # 64KB chunks
    with open(file_path, "wb") as out_file:
        while chunk := uploaded_file.read(chunk_size):
            out_file.write(chunk)
            
    # Renmae the files in the storage_path to be sanitized
    rename_files_in_folder(storage_path)
    
    # Update the file_path and file_name after sanitization
    file_path = os.path.join(storage_path, sanitize_filename(file_name))
    file_name = sanitize_filename(file_name)
            
    # ✅ Calculate file hash
    file_hash = calculate_md5(file_path)

    logger.info(f"✅ File {file_name} saved successfully at {file_path}")

    return {
        "file_path": file_path,
        "filename": file_name,
        "file_size": uploaded_file.size,
        "file_type": mime_type,
        "md5_hash": file_hash,
        "upload_timestamp": datetime.utcnow().isoformat()
    }


def calculate_md5(file_path: str):
    """Computes MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):  # Read in 4KB chunks
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def convert_pdf_date(raw_date):
    """
    Converts extracted PDF dates to ISO 8601 format (YYYY-MM-DD HH:MM:SS).
    Handles:
      - PDF format: "D:20250302161655+00'00'"
      - Human-readable format: "Sun Mar  2 10:16:55 2025 CST"
    """
    if not raw_date or not isinstance(raw_date, str):
        return None

    # ✅ Handle PDF Standard Date Format: "D:20250302161655+00'00'"
    pdf_date_match = re.match(r"D:(\d{14})([+-]\d{2})'(\d{2})'", raw_date)
    if pdf_date_match:
        date_part = pdf_date_match.group(1)  # Extract "20250302161655"
        tz_offset_hours = int(pdf_date_match.group(2))  # Extract "+00"
        tz_offset_minutes = int(pdf_date_match.group(3))  # Extract "00"

        # Convert to datetime object
        parsed_date = datetime.strptime(date_part, "%Y%m%d%H%M%S")

        # Apply timezone offset
        tz_offset = timedelta(hours=tz_offset_hours, minutes=tz_offset_minutes)
        parsed_date = parsed_date - tz_offset  # Adjust time based on timezone offset

        print(f"✅ PDF Parsed Date: {parsed_date.isoformat()}")
        return parsed_date.isoformat()

    # ✅ Handle Human-Readable Date: "Sun Mar  2 10:16:55 2025 CST"
    try:
        parsed_date = dateutil.parser.parse(raw_date)
        print(f"✅ Human-Readable Parsed Date: {parsed_date.isoformat()}")
        return parsed_date.isoformat()
    except Exception as e:
        print(f"❌ Error parsing date '{raw_date}': {e}")
        return None

def extract_pdf_metadata(pdf_path):
    """
    Extracts extensive metadata from a PDF file using multiple libraries.
    
    :param pdf_path: Path to the PDF document.
    :return: Dictionary containing cleaned metadata.
    """
    if not os.path.exists(pdf_path):
        return {"Error": "File not found"}

    metadata = {}

    # ✅ Step 1: Extract metadata using PyMuPDF (fitz)
    doc = fitz.open(pdf_path)
    raw_metadata = doc.metadata or {}  # Add standard metadata fields
    metadata.update({k.lower(): v for k, v in raw_metadata.items()})  # Normalize keys
    
    # ✅ Fix date fields to ISO 8601
    metadata["creationdate"] = convert_pdf_date(metadata.get("creationdate"))
    metadata["moddate"] = convert_pdf_date(metadata.get("moddate"))

    metadata["file_size"] = os.path.getsize(pdf_path)  # File size in bytes
    metadata["page_count"] = len(doc)  # Number of pages

    metadata["is_encrypted"] = str_to_bool(raw_metadata.get("is_encrypted", "no"))
    metadata["encrypted"] = str_to_bool(raw_metadata.get("encrypted", "no"))
    metadata["optimized"] = str_to_bool(raw_metadata.get("optimized", "no"))

    # ✅ Handle PDF version safely
    metadata["pdf_version"] = raw_metadata.get("format", "Unknown PDF Version")

    # ✅ Step 2: Extract font information
    fonts = set()
    for page in doc:
        for font in page.get_fonts(full=True):
            fonts.add(font[3])  # Extracting font names
    metadata["fonts"] = list(fonts) if fonts else "No font information available"

    # ✅ Step 3: Extract additional metadata using PyPDF2
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        doc_info = reader.metadata
        metadata.update({k.lower(): v for k, v in (doc_info or {}).items()})  # Normalize keys
 
        # 🔐 Normalize all known boolean fields to Python bools
        for key in [
            "is_encrypted", "encrypted", "optimized", "tagged",
            "userproperties", "suspects", "custom_metadata"
        ]:
            if key in metadata:
                metadata[key] = str_to_bool(metadata[key])

        metadata["page_rotation"] = [page.rotation for page in reader.pages]  # Page rotation angles

    # ✅ Step 4: Extract document metadata using pdfminer.six
    with open(pdf_path, "rb") as f:
        parser = PDFParser(f)
        doc = PDFDocument(parser)
        pdfminer_info = {k: v.decode("utf-8", "ignore") if isinstance(v, bytes) else v for k, v in doc.info[0].items()}
        metadata.update({k.lower(): v for k, v in pdfminer_info.items()})  # Normalize keys
        
        # 🔐 Normalize all known boolean fields to Python bools
        for key in [
            "is_encrypted", "encrypted", "optimized", "tagged",
            "userproperties", "suspects", "custom_metadata"
        ]:
            if key in metadata:
                metadata[key] = str_to_bool(metadata[key])

    # ✅ Step 5: Extract even more details using pdfinfo (Poppler)
    try:
        pdfinfo_output = subprocess.run(
            ["pdfinfo", pdf_path], capture_output=True, text=True
        )
        pdfinfo_data = pdfinfo_output.stdout.strip().split("\n")
        for line in pdfinfo_data:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower().replace(" ", "_")] = value.strip()
    except Exception as e:
        metadata["pdfinfo_error"] = str(e)

    # ✅ Step 6: Convert Date Fields to Readable Format
    # for date_key in ["creation_date", "moddate"]:
        # if date_key in metadata and metadata[date_key]:
            # try:
                # metadata[date_key] = datetime.strptime(metadata[date_key][2:16], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            # except ValueError:
                # pass  # Keep as is if format is unrecognized

    return metadata


def extract_docx_metadata(docx_path):
    metadata = {
        "format": "DOCX",
        "title": None,
        "author": None,
        "subject": None,
        "keywords": None,
        "creator": None,
        "producer": None,
        "creationdate": None,
        "moddate": None,
        "last_modified_by": None,
        "category": None,
        "content_status": None,
        "revision": None,
        "trapped": None,
        "encryption": None,
        "file_size": os.path.getsize(docx_path),
        "page_count": None,
        "is_encrypted": False,
        "fonts": [],
        "page_rotation": None,
        "pdfminer_info": None,
        "metadata_stream": None,
        "tagged": None,
        "userproperties": None,
        "suspects": None,
        "form": None,
        "javascript": None,
        "pages": None,
        "encrypted": False,
        "page_size": None,
        "optimized": False,
        "pdf_version": None,
        "word_count": None,
    }

    # Extract metadata from DOCX ZIP format (docProps/core.xml)
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx_zip:
            if "docProps/core.xml" in docx_zip.namelist():
                core_xml = docx_zip.read("docProps/core.xml").decode("utf-8")
                
                # Parse XML
                root = ET.fromstring(core_xml)
                ns = {
                    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
                    "dc": "http://purl.org/dc/elements/1.1/",
                    "dcterms": "http://purl.org/dc/terms/"
                }

                # Extract standard metadata fields
                metadata["title"] = root.findtext("dc:title", default=None, namespaces=ns)
                metadata["creator"] = root.findtext("dc:creator", default=None, namespaces=ns)
                metadata["subject"] = root.findtext("dc:subject", default=None, namespaces=ns)
                metadata["keywords"] = root.findtext("cp:keywords", default=None, namespaces=ns)
                metadata["last_modified_by"] = root.findtext("cp:lastModifiedBy", default=None, namespaces=ns)
                metadata["category"] = root.findtext("cp:category", default=None, namespaces=ns)
                metadata["content_status"] = root.findtext("cp:contentStatus", default=None, namespaces=ns)
                metadata["revision"] = root.findtext("cp:revision", default=None, namespaces=ns)
                

                # Handle creation and modification dates safely
                created_date = root.find("dcterms:created", ns)
                modified_date = root.find("dcterms:modified", ns)
                
                if created_date is not None and created_date.text:
                    try:
                        # Pass only the string to convert_pdf_date()
                        metadata["creationdate"] = convert_pdf_date(created_date.text)
                    except ValueError:
                        metadata["creationdate"] = None  # Handle parsing failure gracefully
                
                if modified_date is not None and modified_date.text:
                    try:
                        # Pass only the string to convert_pdf_date()
                        metadata["moddate"] = convert_pdf_date(modified_date.text)
                    except ValueError:
                        metadata["moddate"] = None  # Handle parsing failure gracefully


                # Handle creation and modification dates safely
                # created_date = root.find("dcterms:created", ns)
                # modified_date = root.find("dcterms:modified", ns)
# 
                # if created_date is not None and created_date.text:
                    # try:
                        # metadata["creationdate"] = convert_pdf_date(datetime.strptime(created_date.text, "%Y-%m-%dT%H:%M:%SZ"))
                    # except ValueError:
                        # metadata["creationdate"] = convert_pdf_date(created_date.text)  # Keep original format if parsing fails
# 
                # if modified_date is not None and modified_date.text:
                    # try:
                        # metadata["moddate"] = convert_pdf_date(datetime.strptime(modified_date.text, "%Y-%m-%dT%H:%M:%SZ"))
                    # except ValueError:
                        # metadata["moddate"] = convert_pdf_date(modified_date.text)  # Keep original format if parsing fails

    except Exception as e:
        metadata["custom_metadata"] = f"Error extracting core.xml: {str(e)}"

    # Extract word count and fonts using `python-docx`
    try:
        doc = Document(docx_path)
        metadata["page_count"] = len(doc.paragraphs) // 20  # Approximate: 20 paragraphs ≈ 1 page
        metadata["word_count"] = sum(len(p.text.split()) for p in doc.paragraphs)
        metadata["fonts"] = list(set(run.font.name for para in doc.paragraphs for run in para.runs if run.font.name))
    except Exception as e:
        metadata["custom_metadata"] += f"\nError extracting document fonts: {str(e)}"


    try:
        metadata["encrypted"] = str_to_bool(raw_metadata.get("encrypted", "no"))
        metadata["is_encrypted"] = str_to_bool(raw_metadata.get("is_encrypted", "no"))
        metadata["optimized"] = str_to_bool(raw_metadata.get("optimized", "no"))
    except Exception as e:
        metadata["custom_metadata"] += f"\nError extracting encrypted/optimized fields: {str(e)}"


    return metadata


def extract_metadata(file_instance):
    """
    Extracts metadata from a given file.

    :param file_instance: File instance from the database
    :return: Metadata dictionary
    """
    file_path = file_instance.filepath
    logger.info(f"🔍 Checking file path: {file_path}")

    # ✅ Check if file exists
    if not Path(file_path).exists():
        logger.error(f"❌ File does not exist: {file_path}")
        return None

    logger.info(f"✅ File found! Extracting metadata for {file_path}")

    metadata = {
        "file_id": file_instance.id,
        "storage_id": file_instance.storage.storage_id if file_instance.storage else None,
        "file_size": os.path.getsize(file_path),
        "format": mimetypes.guess_type(file_path)[0] or "unknown",
        "md5_hash": file_instance.md5_hash or None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "title": None,
        "author": None,
        "subject": None,
        "keywords": None,
        "creator": None,
        "producer": None,
        "creationdate": None,
        "moddate": None,
        "last_modified_by": None,
        "category": None,
        "content_status": None,
        "revision": None,
        "trapped": None,
        "encryption": "No",
        "page_count": None,
        "is_encrypted": False,
        "fonts": [],
        "page_rotation": None,
        "pdfminer_info": None,
        "metadata_stream": None,
        "tagged": None,
        "userproperties": None,
        "suspects": None,
        "form": None,
        "javascript": None,
        "pages": None,
        "encrypted": False,
        "page_size": None,
        "optimized": False,
        "pdf_version": None,
        "word_count": None,
    }


    # ✅ Extract metadata for PDFs
    if file_instance.filename.endswith(".pdf"):
        try:
            pdf_metadata = extract_pdf_metadata(file_path)
            metadata.update(pdf_metadata)
            logger.info(f"✅ Extracted PDF metadata: {pdf_metadata}")
        except Exception as e:
            logger.error(f"❌ PDF metadata extraction failed: {str(e)}")

    # ✅ Extract metadata for DOCX
    elif file_instance.filename.endswith(".docx"):
        try:
            docx_metadata = extract_docx_metadata(file_path)
            metadata.update(docx_metadata)
            logger.info(f"✅ Extracted DOCX metadata: {docx_metadata}")
        except Exception as e:
            logger.error(f"❌ DOCX metadata extraction failed: {str(e)}")

    # ✅ Extract word count for TXT
    elif file_instance.filename.endswith(".txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as text_file:
                metadata["word_count"] = sum(len(line.split()) for line in text_file)
            logger.info(f"✅ Extracted TXT metadata: {metadata}")
        except Exception as e:
            logger.error(f"❌ TXT metadata extraction failed: {str(e)}")

    return metadata



def register_generated_file(file_path, user, run, project_id, service_id, folder_name="generated"):
    """
    Registers any generated file (e.g., translated, anonymized) in the File table
    using a flexible GenericForeignKey to support any run type.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot register missing file: {file_path}")

    # Calculate MD5
    with open(file_path, "rb") as f:
        content = f.read()
        md5_hash = hashlib.md5(content).hexdigest()

    # Get content type for the given run
    content_type = ContentType.objects.get_for_model(run)

    # ✅ Create Storage with generic linkage
    storage = Storage.objects.create(
        user=user,
        content_type=content_type,
        object_id=run.pk,
        upload_storage_location=file_path,
        output_storage_location=None
    )

    # ✅ Register File with link to Storage and optionally Run
    from core.models import Run
    file_instance = File.objects.create(
        run=run if isinstance(run, Run) else None,
        storage=storage,
        filename=os.path.basename(file_path),
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=os.path.splitext(file_path)[1].lstrip("."),
        md5_hash=md5_hash,
        user=user,
        project_id=project_id,
        service_id=service_id,
    )

    # ✅ Link to folder
    from document_operations.models import Folder, FileFolderLink
    folder, _ = Folder.objects.get_or_create(
        name=folder_name,
        user=user,
        project_id=project_id,
        service_id=service_id,
        defaults={"created_at": timezone.now()}
    )
    FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)

    return file_instance




'''
def register_generated_file(file_path, user, run, project_id, service_id, folder_name="generated", translation_run=None):
    """
    Registers any generated file (e.g., anonymized, translated) into the File table
    with proper folder linkage, mimicking the upload pipeline.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot register missing file: {file_path}")

    # Calculate MD5 hash
    with open(file_path, "rb") as f:
        content = f.read()
        md5_hash = hashlib.md5(content).hexdigest()

    # Create a Storage entry with the translation_run if it exists
    if translation_run:
        storage = Storage.objects.create(user=user, translation_run=translation_run, upload_storage_location=file_path)
    else:
        storage = Storage.objects.create(user=user, run=run, upload_storage_location=file_path)

    # Create the File entry
    file_instance = File.objects.create(
        run=run,
        storage=storage,
        filename=os.path.basename(file_path),
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=os.path.splitext(file_path)[1].lstrip("."),
        md5_hash=md5_hash,
        user=user,
        project_id=project_id,
        service_id=service_id,
    )

    # Link the file to a folder
    folder, _ = Folder.objects.get_or_create(
        name=folder_name,
        user=user,
        project_id=project_id,
        service_id=service_id,
        defaults={"created_at": timezone.now()}
    )
    FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)

    return file_instance
'''



'''
def register_generated_file(file_path, user, run, project_id, service_id, folder_name="generated"):
    """
    Registers any generated file (e.g., anonymized, translated) into the File table
    with proper folder linkage, mimicking the upload pipeline.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot register missing file: {file_path}")

    # Calculate MD5 hash
    with open(file_path, "rb") as f:
        content = f.read()
        md5_hash = hashlib.md5(content).hexdigest()

    # Create or fetch Storage entry
    # Ensure this is the correct `run` (either `Run` for anonymization or `TranslationRun` for translation)
    storage = Storage.objects.create(user=user, run=run, upload_storage_location=file_path)

    # Create the File entry
    file_instance = File.objects.create(
        run=run,  # Link to the correct `run` (either `Run` or `TranslationRun`)
        storage=storage,
        filename=os.path.basename(file_path),
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=os.path.splitext(file_path)[1].lstrip("."),
        md5_hash=md5_hash,
        user=user,
        project_id=project_id,
        service_id=service_id,
    )

    # Link the file to a folder
    folder, _ = Folder.objects.get_or_create(
        name=folder_name,
        user=user,
        project_id=project_id,
        service_id=service_id,
        defaults={"created_at": timezone.now()}
    )
    FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)

    return file_instance
'''




'''
def register_generated_file(file_path, user, run, project_id, service_id, folder_name="generated"):
    """
    Registers any generated file (e.g., anonymized, translated) into the File table
    with proper folder linkage, mimicking the upload pipeline.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot register missing file: {file_path}")

    # Calculate MD5 hash
    with open(file_path, "rb") as f:
        content = f.read()
        md5_hash = hashlib.md5(content).hexdigest()

    # Create a Storage entry
    storage = Storage.objects.create(user=user, run=run, upload_storage_location=file_path)

    # Create the File entry
    file_instance = File.objects.create(
        run=run,
        storage=storage,
        filename=os.path.basename(file_path),
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=os.path.splitext(file_path)[1].lstrip("."),
        md5_hash=md5_hash,
        user=user,
        project_id=project_id,
        service_id=service_id,
    )

    # Link the file to a folder
    folder, _ = Folder.objects.get_or_create(
        name=folder_name,
        user=user,
        project_id=project_id,
        service_id=service_id,
        defaults={"created_at": timezone.now()}
    )
    FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)

    return file_instance

'''
