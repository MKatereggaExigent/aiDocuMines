"""
document_search.utils
~~~~~~~~~~~~~~~~~~~~

Shared utilities for text extraction, chunking, and embedding.

Supported file types:
- .pdf     → PyMuPDF
- .docx    → python-docx
- .xlsx    → openpyxl
- .xls     → xlrd
- .txt     → plain text
- .json    → JSON → pretty string
- .html    → BeautifulSoup text
- .md      → plain markdown text
- .jpg/.jpeg/.png → OCR (Tesseract)

Public API:
- extract_text(path: str)                   → str
- split_text(text: str)                     → list[str]
- embed_texts(list[str])                    → list[list[float]]
- compute_chunks(path)                      → tuple[list[str], list[float]]
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from functools import lru_cache
from typing import List, Tuple
from core.models import File
from unstructured.partition.pdf import partition_pdf
import nltk
from nltk.tokenize import sent_tokenize
nltk.download('punkt')

from pathlib import Path
import os
import logging
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.html import partition_html

LOGGER = logging.getLogger(__name__)

# ─────────── Optional dependencies (fail-safe) ─────────────
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise RuntimeError("Install with: pip install sentence-transformers") from e

# ──────────────── Defaults / Config overrides ──────────────
try:
    from document_search import config
    MODEL_NAME = getattr(config, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE = getattr(config, "CHUNK_SIZE", 500)
    CHUNK_OVERLAP = getattr(config, "CHUNK_OVERLAP", 100)
except ImportError:
    MODEL_NAME = "all-MiniLM-L6-v2"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100

LOGGER = logging.getLogger(__name__)


def safe_metadata_to_dict(metadata):
    """
    Recursively converts unstructured metadata objects to JSON-safe dicts.
    """
    if metadata is None:
        return None
    if hasattr(metadata, "to_dict"):
        return safe_metadata_to_dict(metadata.to_dict())
    elif isinstance(metadata, dict):
        return {k: safe_metadata_to_dict(v) for k, v in metadata.items()}
    elif isinstance(metadata, (list, tuple)):
        return [safe_metadata_to_dict(item) for item in metadata]
    elif isinstance(metadata, (str, int, float, bool)):
        return metadata
    else:
        # fallback to string representation
        return str(metadata)


# ─────────────── Embeddings ────────────────────────────────
@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    LOGGER.info("🔄 Loading embedding model '%s'...", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = _get_model()
    return model.encode(texts, show_progress_bar=False).tolist()


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]


# ─────────────── Chunking ──────────────────────────────────
'''
def split_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    """Split long text into overlapping chunks with optional truncation."""
    if not text:
        return []

    text = text.strip()
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk[:1000])  # truncate to Milvus VARCHAR limit
        start += chunk_size - overlap

    return chunks
'''


def split_text(text: str, chunk_size=500, overlap=100) -> List[str]:
    sentences = sent_tokenize(text)
    chunks = []
    chunk = ""

    for sentence in sentences:
        if len(chunk) + len(sentence) <= chunk_size:
            chunk += " " + sentence
        else:
            chunks.append(chunk.strip())
            # Add overlap
            chunk = sentence[-overlap:] if len(sentence) > overlap else sentence

    if chunk:
        chunks.append(chunk.strip())

    return chunks


# ─────────────── Extractors ────────────────────────────────
def _extract_pdf(path: Path) -> str:
    if fitz is None:
        LOGGER.warning("❌ PyMuPDF not installed; skipping .pdf")
        return ""
    try:
        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        LOGGER.error("❌ PDF extract failed [%s]: %s", path.name, e)
        return ""


def _extract_docx(path: Path) -> str:
    if Document is None:
        LOGGER.warning("❌ python-docx not installed; skipping .docx")
        return ""
    try:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        LOGGER.error("❌ DOCX extract failed [%s]: %s", path.name, e)
        return ""


def _extract_xlsx(path: Path) -> str:
    if openpyxl is None:
        LOGGER.warning("❌ openpyxl not installed; skipping .xlsx")
        return ""
    try:
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        rows = [
            str(cell)
            for sheet in wb.worksheets
            for row in sheet.iter_rows(values_only=True)
            for cell in row if cell
        ]
        return "\n".join(rows)
    except Exception as e:
        LOGGER.error("❌ XLSX extract failed [%s]: %s", path.name, e)
        return ""


def _extract_xls(path: Path) -> str:
    if xlrd is None:
        LOGGER.warning("❌ xlrd not installed; skipping .xls")
        return ""
    try:
        book = xlrd.open_workbook(str(path))
        return "\n".join(
            str(cell.value)
            for sheet in book.sheets()
            for r in range(sheet.nrows)
            for cell in sheet.row(r)
            if cell.value
        )
    except Exception as e:
        LOGGER.error("❌ XLS extract failed [%s]: %s", path.name, e)
        return ""


def _extract_txt(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        LOGGER.error("❌ TXT read failed [%s]: %s", path.name, e)
        return ""


def _extract_json(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    except Exception as e:
        LOGGER.error("❌ JSON load failed [%s]: %s", path.name, e)
        return ""


def _extract_html(path: Path) -> str:
    if BeautifulSoup is None:
        LOGGER.warning("❌ beautifulsoup4 not installed; skipping .html")
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
            return soup.get_text(separator="\n")
    except Exception as e:
        LOGGER.error("❌ HTML extract failed [%s]: %s", path.name, e)
        return ""


def _extract_image(path: Path) -> str:
    if Image is None or pytesseract is None:
        LOGGER.debug("📸 OCR libs not installed; skipping image")
        return ""
    try:
        img = Image.open(str(path))
        return pytesseract.image_to_string(img)
    except Exception as e:
        LOGGER.error("❌ OCR failed [%s]: %s", path.name, e)
        return ""


_EXTRACTORS = {
    ".pdf":   _extract_pdf,
    ".docx":  _extract_docx,
    ".xlsx":  _extract_xlsx,
    ".xls":   _extract_xls,
    ".txt":   _extract_txt,
    ".md":    _extract_txt,
    ".json":  _extract_json,
    ".html":  _extract_html,
    ".htm":   _extract_html,
    ".jpg":   _extract_image,
    ".jpeg":  _extract_image,
    ".png":   _extract_image,
}

'''
def extract_text(path: str | os.PathLike) -> str:
    """Extract raw text from supported filetypes. Returns '' if unsupported."""
    p = Path(path)
    ext = p.suffix.lower()
    extractor = _EXTRACTORS.get(ext)

    if not extractor:
        LOGGER.info("ℹ️ Unsupported extension '%s'; skipping %s", ext, p.name)
        return ""

    return extractor(p)
'''


def extract_text(path: str | os.PathLike) -> str:
    """Extract raw text from supported filetypes using unstructured or fallback extractors."""
    p = Path(path)
    ext = p.suffix.lower()

    try:
        if ext == ".pdf":
            elements = partition_pdf(filename=str(p))
            return "\n\n".join(el.text for el in elements if el.text)

        elif ext == ".docx":
            elements = partition_docx(filename=str(p))
            return "\n\n".join(el.text for el in elements if el.text)

        elif ext in [".html", ".htm"]:
            elements = partition_html(filename=str(p))
            return "\n\n".join(el.text for el in elements if el.text)

        elif ext == ".txt":
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".md":
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        else:
            LOGGER.info("ℹ️ Unsupported extension '%s'; skipping %s", ext, p.name)
            return ""

    except Exception as e:
        LOGGER.error("❌ Failed to extract text from [%s]: %s", p.name, e)
        return ""


# ─────────────── High-level pipeline ───────────────────────
def compute_chunks(
    path: str | os.PathLike,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> Tuple[List[str], List[List[float]]]:
    """
    Full pipeline: file ➤ text ➤ chunks ➤ vectors.

    Returns:
        (chunks, vectors)
    """
    text = extract_text(path)
    if not text.strip():
        return [], []

    chunks = split_text(text, chunk_size, overlap)
    vectors = embed_texts(chunks)
    return chunks, vectors


# document_search/utils.py


def preview_for_file(file_id: int) -> dict:
    f = File.objects.filter(pk=file_id).first()
    
    from django.core.signing import Signer
    signer = Signer()

    if not f:
        return {}
    return {
        "filename": f.filename,
        "signed_url": f"/api/download/?token=" + signer.sign(f.id),         # optionally wrap with signer for security
        "size": f.file_size,
        "mime": f.file_type,
    }

