import pdfplumber
import pytesseract
from pdf2image import convert_from_path

class PDFReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read_pdf(self):
        with pdfplumber.open(self.file_path) as pdf:
            type_file = self.identify_type_content(pdf)
            if type_file == "plain_text":
                return self.extract_text_from_file(self.file_path)
            elif type_file == "image":
                return self.extract_text_from_image(self.file_path)

    @staticmethod
    def identify_type_content(file):
        for i, pages in enumerate(file.pages):
            text = pages.extract_text()
            timages = len(pages.images) > 0 or len(pages.images) > 0
            if text and text.strip():
                return "plain_text"
            elif timages:
                return "image"
        return "unknown"

    @staticmethod
    def extract_text_from_file(file_path):
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text.strip()

    @staticmethod
    def extract_text_from_image(file_path, language="spa"):
        pages_with_images = convert_from_path(file_path, dpi=300)
        complete_text = []
        for i, page in enumerate(pages_with_images):
            text = pytesseract.image_to_string(page, lang=language)
            if text and text.strip():
                complete_text.append(text.strip())
        return "\n".join(complete_text)