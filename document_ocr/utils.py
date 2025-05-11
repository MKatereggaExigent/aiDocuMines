import os
import subprocess
import logging
import shutil
import uuid
import fitz  # PyMuPDF
import pandas as pd
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from django.conf import settings
from django.utils.timezone import now
from django.db import transaction
from django.shortcuts import get_object_or_404
from docx import Document
from core.models import File
from document_ocr.models import OCRFile, OCRRun

# Configure logging
logger = logging.getLogger(__name__)

# Try importing Adobe PDF Services SDK, otherwise fallback
try:
    from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
    from adobe.pdfservices.operation.pdf_services import PDFServices
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
    from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult
    ADOBE_PDF_SERVICES_AVAILABLE = True
except ImportError:
    ADOBE_PDF_SERVICES_AVAILABLE = False
    logger.warning("⚠️ Adobe PDF Services SDK is not installed. Falling back to Pandoc for DOCX conversion.")


class OCRService:
    """Handles OCR processing for PDF files."""

    def get_file_path(self, file_id):
        """Retrieve file path from `core.models.File`."""
        file_obj = File.objects.filter(id=file_id).first()
        if not file_obj:
            logger.error(f"❌ File ID {file_id} not found.")
            return None
        return file_obj.filepath if os.path.exists(file_obj.filepath) else None

    def is_pdf(self, file_path):
        """Check if the file is a valid PDF."""
        try:
            with open(file_path, "rb") as f:
                PdfReader(f)
            return True
        except:
            return False

    def get_output_path(self, file_id, file_path):
        """Generates structured output path for OCRed files."""
        base_name = os.path.basename(file_path)
        output_path = os.path.join(os.path.dirname(file_path), "ocr", f"ocr-{base_name}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return output_path


    def burst_pdf(self, file_path, batch_size=10):
        """Splits a PDF into smaller batches for OCR processing."""
        pdf_reader = PdfReader(file_path)
        total_pages = len(pdf_reader.pages)
        
        # ✅ **Ensure single `ocr/tmp/` structure**
        ocr_dir = os.path.join(os.path.dirname(file_path), "ocr")
        tmp_dir = os.path.join(ocr_dir, "tmp")  # ✅ Clean structure
        os.makedirs(tmp_dir, exist_ok=True)
    
        burst_files = []
        for start_page in range(0, total_pages, batch_size):
            end_page = min(start_page + batch_size, total_pages)
            pdf_writer = PdfWriter()
    
            for page in range(start_page, end_page):
                pdf_writer.add_page(pdf_reader.pages[page])
    
            burst_filepath = os.path.join(tmp_dir, f"ocr-part-{uuid.uuid4()}.pdf")
            with open(burst_filepath, "wb") as batch_file:
                pdf_writer.write(batch_file)
    
            burst_files.append((start_page + 1, end_page, burst_filepath))
    
        return burst_files

    
    
    def merge_pdf(self, pdf_files, output_path):
        """Merges multiple PDFs into a single file, ensuring all parts are included."""
        merger = PdfMerger()
    
        for pdf in pdf_files:
            if os.path.exists(pdf):  # ✅ Ensure the file exists before adding
                merger.append(pdf)
            else:
                logger.error(f"❌ Missing OCR batch: {pdf}")
    
        if len(merger.pages) == 0:
            logger.error("❌ No valid OCR'ed pages found. Merging failed.")
            return None
    
        with open(output_path, "wb") as output_file:
            merger.write(output_file)
    
        return output_path


    def apply_ocr(self, file_id, file_path, ocr_option="basic"):
        """Applies OCR to a given PDF file and saves the OCRed file."""
        if not file_path or not self.is_pdf(file_path):
            logger.info(f"🔹 Skipping OCR: File {file_path} is not a PDF.")
            return None
    
        ocr_dir = os.path.join(os.path.dirname(file_path), "ocr")
        tmp_dir = os.path.join(ocr_dir, "tmp")  # ✅ Consistent structure
        os.makedirs(tmp_dir, exist_ok=True)
    
        # ✅ Store OCR output in `tmp/`
        ocr_output_path = os.path.join(tmp_dir, f"ocr-{uuid.uuid4()}.pdf")
    
        try:
            logger.info(f"🔄 Applying OCR to {file_path}")
    
            cmd = [
                "ocrmypdf",
                "--optimize", "1",
                "--force-ocr",
                "--rotate-pages",
                file_path,
                ocr_output_path
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
    
            if process.returncode != 0:
                logger.error(f"❌ OCR failed: {process.stderr}")
                return None
    
            # ✅ Ensure OCR output exists
            if not os.path.exists(ocr_output_path):
                logger.error(f"❌ OCR output file missing: {ocr_output_path}")
                return None
    
            return ocr_output_path
    
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ OCR processing failed: {e.stderr}")
            return None
    

    def convert_to_formatted_docx(self, pdf_path, output_path):
        """Converts OCRed PDF to **Formatted DOCX** using Adobe PDF Services."""
        if not ADOBE_PDF_SERVICES_AVAILABLE:
            logger.warning("⚠️ Adobe PDF Services not available. Skipping formatted DOCX conversion.")
            return None
    
        try:
            credentials = ServicePrincipalCredentials(
                client_id=os.getenv("PDF_SERVICES_CLIENT_ID"),
                client_secret=os.getenv("PDF_SERVICES_CLIENT_SECRET")
            )
            pdf_services = PDFServices(credentials=credentials)
    
            with open(pdf_path, "rb") as file:
                input_stream = file.read()
    
            input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)
            export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX)
            export_pdf_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_pdf_params)
    
            location = pdf_services.submit(export_pdf_job)
            pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)
            result_asset = pdf_services_response.get_result().get_asset()
            stream_asset = pdf_services.get_content(result_asset)
    
            with open(output_path, "wb") as docx_file:
                docx_file.write(stream_asset.get_input_stream())
    
            return output_path
    
        except Exception as e:
            logger.error(f"❌ Formatted DOCX conversion failed: {e}")
            return None
    

        
    def reattach_bookmarks_from_dataframe(self, output_pdf, df_bookmarks, start_page, end_page):
        """
        Reattach bookmarks to the extracted pages using the pandas DataFrame.
        Handles issues related to incremental saving and encryption.
        """
        pdf_document = fitz.open(output_pdf)
        toc = []
    
        # ✅ Create a backup filename to avoid overwriting errors
        temp_output_pdf = output_pdf.replace(".pdf", "_temp.pdf")
    
        # ✅ Apply bookmarks from DataFrame
        for _, row in df_bookmarks.iterrows():
            if start_page - 1 <= row["page"] < end_page:
                adjusted_page_num = row["page"] - (start_page - 1) + 1
                toc.append([row["line"], row["bookmark"], adjusted_page_num])
    
        pdf_document.set_toc(toc)
        pdf_document.close()  # ✅ Ensure file is closed before saving
    
        try:
            # ✅ Save with a new filename to avoid conflicts
            pdf_document = fitz.open(output_pdf)  # Reopen after closing
            pdf_document.save(temp_output_pdf, incremental=False)
            pdf_document.close()
    
            # ✅ Rename the temp file back to the original output filename
            os.rename(temp_output_pdf, output_pdf)
            logger.info(f"✅ Final PDF with bookmarks saved to {output_pdf}")
    
        except Exception as e:
            logger.error(f"❌ Failed to reattach bookmarks: {e}")
            if os.path.exists(temp_output_pdf):
                os.remove(temp_output_pdf)  # Cleanup failed file

 
    def convert_to_docx(self, pdf_path):
        """Converts an OCRed PDF to a formatted DOCX using Adobe PDF Services."""
        try:
            # ✅ Load Adobe API credentials
            credentials = ServicePrincipalCredentials(
                client_id=os.getenv('PDF_SERVICES_CLIENT_ID'),
                client_secret=os.getenv('PDF_SERVICES_CLIENT_SECRET')
            )
            pdf_services = PDFServices(credentials=credentials)

            # ✅ Open the PDF file
            with open(pdf_path, 'rb') as file:
                input_stream = file.read()

            # ✅ Upload PDF to Adobe API
            input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

            # ✅ Set up the export job for DOCX conversion
            export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX)
            export_pdf_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_pdf_params)

            # ✅ Submit job and get results
            location = pdf_services.submit(export_pdf_job)
            pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)
            result_asset = pdf_services_response.get_result().get_asset()
            stream_asset = pdf_services.get_content(result_asset)

            # ✅ Save DOCX file
            docx_output_path = pdf_path.replace('.pdf', '_OCRed.docx')
            with open(docx_output_path, "wb") as docx_file:
                docx_file.write(stream_asset.get_input_stream())

            return docx_output_path

        except Exception as e:
            logger.error(f"❌ DOCX conversion failed: {e}")
            return None

    def convert_to_raw_docx(self, pdf_path, output_path):
        """Converts OCRed PDF to **Raw DOCX** using Pandoc."""
        try:
            cmd = ["pandoc", pdf_path, "-o", output_path]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Raw DOCX conversion failed: {e.stderr.decode()}")
            return None

 
    def extract_bookmarks_to_dataframe(self, input_pdf):
        """
        Extract bookmarks from the input PDF and store them in a pandas DataFrame.
        """
        bookmarks = []
        pdf_document = fitz.open(input_pdf)
        outlines = pdf_document.get_toc()

        for outline in outlines:
            level, title, page_num = outline
            bookmarks.append({"bookmark": title, "line": level, "page": page_num - 1})

        df_bookmarks = pd.DataFrame(bookmarks)
        pdf_document.close()
        return df_bookmarks


def cleanup_tmp_dir(tmp_dir):
    """Removes temporary directories."""
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.info(f"✅ Cleaned up temporary directory: {tmp_dir}")

def cleanup_temp_files(file_paths):
    """Delete temporary files."""
    for path in file_paths:
        os.remove(path)
        logger.info(f"✅ Deleted temporary file: {path}")