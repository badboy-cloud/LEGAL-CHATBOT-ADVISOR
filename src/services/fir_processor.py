import os
import re
from typing import Optional
from PIL import Image
import pytesseract
import pypdf

class FIRProcessor:
    """
    FIR Document Processing Service.
    Extracts text from PDF, JPG, JPEG, and PNG files using pypdf and pytesseract.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Normalize and clean extracted text.
        """
        if not text:
            return ""
            
        # Replace multiple spaces/newlines with single space/newline
        text = re.sub(r'[ \t]+', ' ', text)
        # Standardize newlines
        text = re.sub(r'\r\n|\r', '\n', text)
        # Limit consecutive newlines to at most 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove obvious OCR noise or byte order marks
        text = text.replace('\ufeff', '')
        
        return text.strip()

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Extract text content from all pages of a PDF document.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        extracted_text = []
        try:
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
        except Exception as e:
            raise RuntimeError(f"Error reading PDF file: {str(e)}")

        return "\n".join(extracted_text)

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        """
        Extract text from an image using Tesseract OCR.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            image = Image.open(file_path)
            # Run pytesseract OCR
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            raise RuntimeError(f"Error running OCR on image: {str(e)}")

    @classmethod
    def process_file(cls, file_path: str) -> str:
        """
        Detect file type and extract text content.
        
        Supports: .pdf, .jpg, .jpeg, .png
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            raw_text = cls.extract_text_from_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png"]:
            raw_text = cls.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only PDF, JPG, JPEG, PNG are supported.")
            
        return cls.clean_text(raw_text)
