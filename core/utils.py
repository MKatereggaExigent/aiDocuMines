# core/utils.py
import os
import re
import csv
import logging
import mimetypes
import zipfile
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

# Third-party libs
from docx import Document
import PyPDF2
import fitz  # PyMuPDF
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from unidecode import unidecode
from tika import parser as tika_parser  # keep as used in extract_document_text
import pandas as pd

from core.models import File, Storage
from document_operations.models import Folder, FileFolderLink
from document_operations.utils import register_file_folder_link

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
    return str(value).strip().lower() in {"true", "yes", "1", "y", "t"}


def sanitize_filename(filename: str) -> str:
    """Sanitize the filename by removing/normalizing special characters."""
    # Replace German/special characters with ASCII
    filename = unidecode(filename)
    # Replace spaces
    filename = filename.replace(" ", "_")
    # Keep only safe chars
    filename = re.sub(r"[^a-zA-Z0-9\-_.]", "", filename)
    return filename


def rename_files_in_folder(folder_path: str) -> None:
    """Renames all files in a folder and subfolders by sanitizing filenames."""
    for root, _, files in os.walk(folder_path):
        for filename in files:
            src = os.path.join(root, filename)
            sanitized = sanitize_filename(filename)
            dst = os.path.join(root, sanitized)
            if src != dst:
                os.rename(src, dst)
                logger.info("Renamed %s -> %s", src, dst)


def save_uploaded_file(uploaded_file, storage_path: str, custom_filename=None):
    """
    Saves uploaded files synchronously.

    :param uploaded_file: File object from Django (InMemoryUploadedFile or TemporaryUploadedFile)
    :param storage_path: System location of uploaded files
    :param custom_filename: Optional new filename (sanitized automatically)
    :return: File metadata dictionary
    """
    # ✅ Validate file size
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")

    # ✅ Validate file type
    file_name = custom_filename or uploaded_file.name
    file_name = sanitize_filename(file_name)
    file_ext = file_name.split(".")[-1].lower()
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    if file_ext not in ALLOWED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {file_ext}")

    os.makedirs(storage_path, exist_ok=True)
    file_path = os.path.join(storage_path, file_name)

    # ✅ Save file in chunks
    chunk_size = 64 * 1024  # 64KB chunks
    with open(file_path, "wb") as out_file:
        while True:
            chunk = uploaded_file.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)

    # Ensure all names in folder are sanitized (idempotent)
    rename_files_in_folder(storage_path)

    # ✅ Calculate file hash
    file_hash = calculate_md5(file_path)
    logger.info("✅ File %s saved at %s", file_name, file_path)

    return {
        "file_path": file_path,
        "filename": file_name,
        "file_size": uploaded_file.size,
        "file_type": mime_type,
        "md5_hash": file_hash,
        "upload_timestamp": datetime.utcnow().isoformat(),
    }


def calculate_md5(file_path: str) -> str:
    """Compute MD5 hash of a file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md5.update(chunk)
    return md5.hexdigest()


def convert_pdf_date(raw_date: str | None):
    """
    Converts extracted PDF (or ISO-ish) dates to ISO 8601 (YYYY-MM-DDTHH:MM:SS).
    Handles:
      - PDF format: "D:20250302161655+00'00'"
      - Generic/ISO-ish strings (best-effort)
    """
    if not raw_date or not isinstance(raw_date, str):
        return None

    # ✅ Handle PDF Standard Date Format
    m = re.match(r"D:(\d{14})([+-]\d{2})'(\d{2})'", raw_date)
    if m:
        date_part = m.group(1)  # "YYYYMMDDHHMMSS"
        tz_h = int(m.group(2))
        tz_m = int(m.group(3))
        try:
            parsed = datetime.strptime(date_part, "%Y%m%d%H%M%S")
            tz = timedelta(hours=tz_h, minutes=tz_m)
            parsed = parsed - tz
            return parsed.isoformat()
        except Exception:
            return None

    # ✅ Fallback: try parsing as generic date
    try:
        # Avoid pulling in dateutil parser globally again
        from dateutil import parser as dateutil_parser  # local import
        return dateutil_parser.parse(raw_date).isoformat()
    except Exception:
        return None


def extract_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract extensive metadata from a PDF using multiple libraries.
    """
    if not os.path.exists(pdf_path):
        return {"Error": "File not found"}

    metadata: dict[str, object] = {}

    # ✅ PyMuPDF (fitz)
    try:
        doc = fitz.open(pdf_path)
        raw = doc.metadata or {}
        metadata.update({k.lower(): v for k, v in raw.items()})
        metadata["file_size"] = os.path.getsize(pdf_path)
        metadata["page_count"] = len(doc)
        metadata["creationdate"] = convert_pdf_date(metadata.get("creationdate"))
        metadata["moddate"] = convert_pdf_date(metadata.get("moddate"))
        metadata["is_encrypted"] = str_to_bool(raw.get("is_encrypted", "no"))
        metadata["encrypted"] = str_to_bool(raw.get("encrypted", "no"))
        metadata["optimized"] = str_to_bool(raw.get("optimized", "no"))
        metadata["pdf_version"] = raw.get("format", "Unknown PDF Version")

        # Fonts
        fonts = set()
        for page in doc:
            for font in page.get_fonts(full=True):
                # tuple layout may vary; index 3 is usually the font name
                if len(font) > 3 and font[3]:
                    fonts.add(font[3])
        metadata["fonts"] = sorted(fonts) if fonts else []
    except Exception as e:
        metadata.setdefault("errors", []).append(f"PyMuPDF error: {e}")

    # ✅ PyPDF2
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            doc_info = reader.metadata or {}
            metadata.update({k.lower(): v for k, v in doc_info.items()})
            try:
                metadata["page_rotation"] = [page.rotation for page in reader.pages]
            except Exception:
                pass

            # normalize common booleans
            for key in [
                "is_encrypted", "encrypted", "optimized", "tagged",
                "userproperties", "suspects", "custom_metadata"
            ]:
                if key in metadata:
                    metadata[key] = str_to_bool(metadata[key])
    except Exception as e:
        metadata.setdefault("errors", []).append(f"PyPDF2 error: {e}")

    # ✅ pdfminer.six
    try:
        with open(pdf_path, "rb") as f:
            p = PDFParser(f)
            d = PDFDocument(p)
            if getattr(d, "info", None):
                # d.info is typically a list of dictionaries
                info0 = d.info[0] if d.info else {}
                info_norm = {
                    (k.decode("utf-8", "ignore") if isinstance(k, bytes) else str(k)).lower():
                    (v.decode("utf-8", "ignore") if isinstance(v, bytes) else v)
                    for k, v in info0.items()
                }
                metadata.update(info_norm)
                for key in [
                    "is_encrypted", "encrypted", "optimized", "tagged",
                    "userproperties", "suspects", "custom_metadata"
                ]:
                    if key in metadata:
                        metadata[key] = str_to_bool(metadata[key])
    except Exception as e:
        metadata.setdefault("errors", []).append(f"pdfminer error: {e}")

    # ✅ pdfinfo (Poppler)
    try:
        out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
        lines = out.stdout.strip().splitlines()
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower().replace(" ", "_")
                metadata[k] = v.strip()
    except Exception as e:
        metadata.setdefault("errors", []).append(f"pdfinfo error: {e}")

    return metadata


def _read_docx_core_props(docx_zip: zipfile.ZipFile) -> dict:
    """Read docProps/core.xml; return normalized fields."""
    core = {}
    if "docProps/core.xml" not in docx_zip.namelist():
        return core
    root = ET.fromstring(docx_zip.read("docProps/core.xml").decode("utf-8"))
    ns = {
        "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dcterms": "http://purl.org/dc/terms/",
    }
    core["title"] = root.findtext("dc:title", default=None, namespaces=ns)
    core["creator"] = root.findtext("dc:creator", default=None, namespaces=ns)
    core["author"] = core.get("creator")  # mirror for convenience
    core["subject"] = root.findtext("dc:subject", default=None, namespaces=ns)
    core["keywords"] = root.findtext("cp:keywords", default=None, namespaces=ns)
    core["last_modified_by"] = root.findtext("cp:lastModifiedBy", default=None, namespaces=ns)
    core["category"] = root.findtext("cp:category", default=None, namespaces=ns)
    core["content_status"] = root.findtext("cp:contentStatus", default=None, namespaces=ns)
    core["revision"] = root.findtext("cp:revision", default=None, namespaces=ns)

    created_node = root.find("dcterms:created", ns)
    modified_node = root.find("dcterms:modified", ns)
    core["creationdate"] = convert_pdf_date(created_node.text) if (created_node is not None and created_node.text) else None
    core["moddate"] = convert_pdf_date(modified_node.text) if (modified_node is not None and modified_node.text) else None
    return core


def _read_docx_custom_props(docx_zip: zipfile.ZipFile) -> dict:
    """Read docProps/custom.xml; return {} if missing."""
    try:
        with docx_zip.open("docProps/custom.xml") as f:
            tree = ET.parse(f)
    except KeyError:
        return {}
    except Exception:
        return {}

    root = tree.getroot()
    ns = {
        "cp": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
        "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
    }
    props = {}
    for prop in root.findall("cp:property", ns):
        name = prop.get("name")
        children = list(prop)
        if not children:
            continue
        value_elem = children[0]
        value = value_elem.text
        props[name] = value
    return props


def extract_docx_metadata(docx_path: str) -> dict:
    """
    DOCX metadata extraction. Always returns a dict that includes 'custom_metadata'.
    """
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
        "encryption": "No",
        "file_size": os.path.getsize(docx_path) if os.path.exists(docx_path) else None,
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
        # 🔐 Always present to avoid KeyError downstream:
        "custom_metadata": {},
    }

    # Extract core & custom props from the package
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            core = _read_docx_core_props(z)
            metadata.update(core)
            metadata["custom_metadata"] = _read_docx_custom_props(z)
    except Exception as e:
        # Keep going; attach error note but preserve key presence
        metadata.setdefault("errors", []).append(f"core/custom props error: {e}")

    # Word count, fonts, rough page estimate via python-docx
    try:
        doc = Document(docx_path)
        paragraphs = list(doc.paragraphs)
        metadata["word_count"] = sum(len(p.text.split()) for p in paragraphs)
        # Very rough page heuristic; better replaced with actual pagination if needed
        metadata["page_count"] = max(1, len(paragraphs) // 20) if paragraphs else 1
        fonts = set()
        for p in paragraphs:
            for run in p.runs:
                if run.font and run.font.name:
                    fonts.add(run.font.name)
        metadata["fonts"] = sorted(fonts) if fonts else []
    except Exception as e:
        metadata.setdefault("errors", []).append(f"python-docx error: {e}")

    # DOCX doesn't really expose encrypted/optimized flags like PDFs; keep defaults
    return metadata


def extract_metadata(file_instance):
    """
    Extracts metadata from a given File model instance.
    """
    file_path = file_instance.filepath
    logger.info("🔍 Checking file path: %s", file_path)

    if not Path(file_path).exists():
        logger.error("❌ File does not exist: %s", file_path)
        return None

    logger.info("✅ File found! Extracting metadata for %s", file_path)

    base = {
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
        # Make sure this key is *always* present
        "custom_metadata": {},
    }

    name_lc = (file_instance.filename or "").lower()

    if name_lc.endswith(".pdf"):
        try:
            pdf_meta = extract_pdf_metadata(file_path)
            base.update(pdf_meta)
            logger.info("✅ Extracted PDF metadata for file_id=%s", file_instance.id)
        except Exception as e:
            logger.error("❌ PDF metadata extraction failed: %s", e)

    elif name_lc.endswith(".docx"):
        try:
            docx_meta = extract_docx_metadata(file_path)
            base.update(docx_meta)
            logger.info("✅ Extracted DOCX metadata for file_id=%s", file_instance.id)
        except Exception as e:
            logger.error("❌ DOCX metadata extraction failed: %s", e)

    elif name_lc.endswith(".txt"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as text_file:
                base["word_count"] = sum(len(line.split()) for line in text_file)
            logger.info("✅ Extracted TXT metadata for file_id=%s", file_instance.id)
        except Exception as e:
            logger.error("❌ TXT metadata extraction failed: %s", e)

    else:
        # leave base as-is; format likely handled elsewhere
        pass

    return base


def register_generated_file(file_path, user, run, project_id, service_id, folder_name="generated"):
    """
    Registers any generated file (e.g., translated, anonymized) in the File table
    using a flexible GenericForeignKey to support any run type.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot register missing file: {file_path}")

    # Calculate MD5
    with open(file_path, "rb") as f:
        md5_hash = hashlib.md5(f.read()).hexdigest()

    # ContentType for the given run instance
    content_type = ContentType.objects.get_for_model(run)

    # ✅ Create Storage with generic linkage
    storage = Storage.objects.create(
        user=user,
        content_type=content_type,
        object_id=run.pk,
        upload_storage_location=file_path,
        output_storage_location=None,
    )

    # De-dup by md5 for this user
    existing = File.objects.filter(md5_hash=md5_hash, user=user).first()
    if existing:
        return existing

    from core.models import Run as RunModel
    file_instance = File.objects.create(
        run=run if isinstance(run, RunModel) else None,
        storage=storage,
        filename=os.path.basename(file_path),
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=mimetypes.guess_type(file_path)[0] or os.path.splitext(file_path)[1].lstrip("."),
        md5_hash=md5_hash,
        user=user,
        project_id=project_id,
        service_id=service_id,
    )

    # Create folder link
    register_file_folder_link(file_instance)
    folder, _ = Folder.objects.get_or_create(
        name=folder_name,
        user=user,
        project_id=project_id,
        service_id=service_id,
        defaults={"created_at": timezone.now()},
    )
    FileFolderLink.objects.get_or_create(file=file_instance, folder=folder)

    return file_instance


def extract_document_text(path, mime_type=None) -> str:
    """
    Extract text from various file types.
    """
    if not os.path.exists(path):
        return ""

    ext = os.path.splitext(path)[-1].lower()
    try:
        if ext == ".pdf":
            text = ""
            doc = fitz.open(path)
            for page in doc:
                text += page.get_text()
            return text

        if ext == ".docx":
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)

        if ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        if ext == ".csv":
            df = pd.read_csv(path, nrows=1000)
            return df.to_string(index=False)

        if ext == ".xlsx":
            df = pd.read_excel(path, nrows=1000)
            return df.to_string(index=False)

        # Fallback for other formats
        parsed = tika_parser.from_file(path)
        return (parsed.get("content") or "").strip()

    except Exception as e:
        return f"Error extracting text: {e}"

