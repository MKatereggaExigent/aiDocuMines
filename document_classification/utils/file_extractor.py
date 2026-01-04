"""
File Extractor

Extracts text content from various document formats for clustering.
"""

import os
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FileExtractor:
    """
    Extracts text content from various document formats.
    Supports PDF, DOCX, TXT, HTML, and other common formats.
    """
    
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.txt': 'text',
        '.rtf': 'rtf',
        '.odt': 'odt',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.csv': 'csv',
        '.pptx': 'pptx',
        '.ppt': 'ppt',
        '.html': 'html',
        '.htm': 'html',
        '.xml': 'xml',
        '.json': 'json',
        '.md': 'markdown',
        '.markdown': 'markdown',
    }
    
    def __init__(self, max_text_length: int = 50000):
        """
        Initialize the file extractor.
        
        Args:
            max_text_length: Maximum text length to extract (for embedding efficiency)
        """
        self.max_text_length = max_text_length
    
    def extract(self, filepath: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Tuple of (extracted_text, error_message)
        """
        if not os.path.exists(filepath):
            return None, f"File not found: {filepath}"
        
        ext = Path(filepath).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return None, f"Unsupported file type: {ext}"
        
        file_type = self.SUPPORTED_EXTENSIONS[ext]
        
        try:
            if file_type == 'pdf':
                return self._extract_pdf(filepath), None
            elif file_type == 'docx':
                return self._extract_docx(filepath), None
            elif file_type == 'text':
                return self._extract_text(filepath), None
            elif file_type == 'html':
                return self._extract_html(filepath), None
            elif file_type == 'excel':
                return self._extract_excel(filepath), None
            elif file_type == 'csv':
                return self._extract_csv(filepath), None
            elif file_type == 'json':
                return self._extract_json(filepath), None
            elif file_type == 'markdown':
                return self._extract_text(filepath), None
            else:
                return self._extract_text(filepath), None
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {e}")
            return None, str(e)
    
    def _extract_pdf(self, filepath: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return self._truncate(text)
        except ImportError:
            # Fallback to pdfplumber
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return self._truncate(text)
    
    def _extract_docx(self, filepath: str) -> str:
        """Extract text from DOCX."""
        from docx import Document
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        return self._truncate(text)
    
    def _extract_text(self, filepath: str) -> str:
        """Extract text from plain text file."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return self._truncate(f.read())
    
    def _extract_html(self, filepath: str) -> str:
        """Extract text from HTML."""
        from bs4 import BeautifulSoup
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            return self._truncate(soup.get_text(separator=' ', strip=True))
    
    def _extract_excel(self, filepath: str) -> str:
        """Extract text from Excel."""
        import pandas as pd
        df = pd.read_excel(filepath, sheet_name=None)
        text = ""
        for sheet_name, sheet_df in df.items():
            text += f"Sheet: {sheet_name}\n"
            text += sheet_df.to_string() + "\n\n"
        return self._truncate(text)
    
    def _extract_csv(self, filepath: str) -> str:
        """Extract text from CSV."""
        import pandas as pd
        df = pd.read_csv(filepath)
        return self._truncate(df.to_string())
    
    def _extract_json(self, filepath: str) -> str:
        """Extract text from JSON."""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return self._truncate(json.dumps(data, indent=2))
    
    def _truncate(self, text: str) -> str:
        """Truncate text to max length."""
        if len(text) > self.max_text_length:
            return text[:self.max_text_length]
        return text

