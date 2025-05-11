# file_readers.py

import pandas as pd
from docx import Document
import fitz
import os
import shutil
import subprocess
import glob

def read_csv_file(file_path):
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

def read_txt_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin1') as f:
            return f.read()

def read_excel_file(file_path):
    ext = file_path.lower().split(".")[-1]
    try:
        if ext == "xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(filename=file_path, data_only=True)
            sheet = wb.active
            data = sheet.values
            columns = next(data)
            return pd.DataFrame(data, columns=columns)
        elif ext == "xls":
            import xlrd
            wb = xlrd.open_workbook(file_path)
            sheet = wb.sheet_by_index(0)
            data = [sheet.row_values(i) for i in range(sheet.nrows)]
            return pd.DataFrame(data[1:], columns=data[0])
        else:
            raise ValueError("Unsupported Excel file format")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return None

def read_docx_file(file_path):
    try:
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return None

def perform_ocr_on_pdf(file_path):
    try:
        output_img_pattern = file_path.replace('.pdf', '_page_%d.png')

        # Step 1: Convert PDF pages to images
        subprocess.run(['magick', '-density', '300', file_path, output_img_pattern], check=True)

        # Step 2: OCR each image to individual PDFs
        ocr_pdfs = []
        for img in sorted(glob.glob(output_img_pattern.replace('%d', '*'))):
            ocr_pdf = img.replace('.png', '.pdf')
            subprocess.run([
                'tesseract',
                img,
                ocr_pdf.replace('.pdf', ''),
                '--oem', '1',
                '--psm', '3',
                'pdf'
            ], check=True)
            ocr_pdfs.append(ocr_pdf)

        # Step 3: Merge OCR PDFs
        merged_pdf = file_path.replace('.pdf', '_OCRed.pdf')
        with open(merged_pdf, 'wb') as out:
            for f in ocr_pdfs:
                with open(f, 'rb') as inp:
                    out.write(inp.read())

        # Step 4: Cleanup temp images and intermediate PDFs
        for f in glob.glob(output_img_pattern.replace('%d', '*')) + ocr_pdfs:
            os.remove(f)

        shutil.move(merged_pdf, file_path)
        return file_path

    except Exception as e:
        print(f"Advanced OCR failed: {e}")
        return file_path

def read_pdf_file(file_path):
    try:
        file_path = perform_ocr_on_pdf(file_path)
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def read_file(file_path):
    if file_path.endswith('.csv'):
        return read_csv_file(file_path), True
    elif file_path.endswith('.txt'):
        return read_txt_file(file_path), False
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        return read_excel_file(file_path), True
    elif file_path.endswith('.docx'):
        return read_docx_file(file_path), False
    elif file_path.endswith('.pdf'):
        return read_pdf_file(file_path), False
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
        return read_image_file(file_path), False
    else:
        print(f"Unsupported file type: {file_path}")
        return None, False

def convert_dataframe_to_text(df):
    return df.to_string() if isinstance(df, pd.DataFrame) else str(df)


def read_image_file(file_path):
    try:
        temp_txt_path = file_path + ".ocr.txt"

        # Run OCR directly on the image (PNG, JPG, etc.)
        subprocess.run([
            'tesseract',
            file_path,
            temp_txt_path.replace(".txt", ""),  # Tesseract appends `.txt`
            '--oem', '1',
            '--psm', '3'
        ], check=True)

        with open(temp_txt_path, 'r') as f:
            text = f.read()

        os.remove(temp_txt_path)
        return text
    except Exception as e:
        print(f"Error reading image OCR: {e}")
        return None

