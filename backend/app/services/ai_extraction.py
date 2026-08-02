import re
from pathlib import Path

TOTAL_RE = re.compile(r"(?:total|amount due)\D{0,20}(\d+[\d,]*\.\d{2})", re.I)
INVOICE_RE = re.compile(r"(?:invoice\s*(?:no|number|#)?)\D{0,10}([A-Z0-9-]+)", re.I)
DATE_RE = re.compile(r"(?:date|invoice date)\D{0,12}(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", re.I)

def read_document_text(path: str) -> str:
    file = Path(path)
    if file.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(file)).pages)
            if text.strip(): return text
        except Exception:
            pass
    if file.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf"}:
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(file))
        except Exception:
            return ""
    return file.read_text(errors="ignore")

def extract_invoice_fields(text: str) -> dict:
    total = TOTAL_RE.search(text or "")
    invoice_number = INVOICE_RE.search(text or "")
    issue_date = DATE_RE.search(text or "")
    amount = float(total.group(1).replace(",", "")) if total else 0.0
    return {"invoice_number": invoice_number.group(1) if invoice_number else "AI-DRAFT", "issue_date": issue_date.group(1) if issue_date else None, "currency": "USD", "subtotal": amount, "tax": 0.0, "total": amount, "confidence": 0.75 if total or invoice_number else 0.35}
