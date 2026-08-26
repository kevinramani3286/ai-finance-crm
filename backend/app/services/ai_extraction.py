import re
from pathlib import Path

TOTAL_RE = re.compile(r"(?:grand\s+total|net\s+amount|amount\s+due|total\s+amount|total)\D{0,30}(?:₹|rs\.?|inr\s*)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
INVOICE_RE = re.compile(r"(?:invoice\s*(?:no|number|#)?|bill\s*(?:no|number|#)?)\D{0,12}([A-Z0-9][A-Z0-9\-/]*)", re.I)
DATE_RE = re.compile(r"(?:invoice\s+date|bill\s+date|date)\D{0,12}(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{4}[\-/]\d{1,2}[\-/]\d{1,2})", re.I)
GSTIN_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", re.I)
PARTY_RE = re.compile(r"(?:bill\s+to|buyer|customer|party|supplier|vendor)\s*[:\-]?\s*([^\n]{3,80})", re.I)
REFERENCE_RE = re.compile(r"(?:utr|transaction\s*(?:id|no)|reference|ref\.?\s*no)\s*[:#\-]?\s*([A-Z0-9\-/]{5,40})", re.I)


def read_document_text(path: str) -> str:
    file = Path(path)
    suffix = file.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(file)).pages)
            if text.strip():
                return text
        except Exception:
            pass
        try:
            from pdf2image import convert_from_path
            import pytesseract
            pages = convert_from_path(str(file), dpi=180, first_page=1, last_page=8)
            return "\n".join(pytesseract.image_to_string(page) for page in pages)
        except Exception:
            return ""
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}:
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(file))
        except Exception:
            return ""
    return file.read_text(errors="ignore")


def _amount(match) -> float:
    return float(match.group(1).replace(",", "")) if match else 0.0


def extract_document_fields(text: str, document_type: str = "invoice") -> dict:
    raw = text or ""
    total = TOTAL_RE.search(raw)
    invoice_number = INVOICE_RE.search(raw)
    issue_date = DATE_RE.search(raw)
    gstin = GSTIN_RE.search(raw)
    party = PARTY_RE.search(raw)
    reference = REFERENCE_RE.search(raw)
    amount = _amount(total)
    confidence_parts = [bool(total), bool(invoice_number), bool(issue_date), bool(gstin), bool(party)]
    confidence = round(sum(confidence_parts) / len(confidence_parts), 2)
    return {
        "document_type": document_type,
        "invoice_number": invoice_number.group(1) if invoice_number else "",
        "issue_date": issue_date.group(1) if issue_date else None,
        "party_name": party.group(1).strip() if party else "",
        "gstin": gstin.group(0).upper() if gstin else "",
        "reference": reference.group(1) if reference else "",
        "currency": "INR",
        "subtotal": amount,
        "tax": 0.0,
        "total": amount,
        "confidence": confidence,
        "text_length": len(raw),
    }


def extract_invoice_fields(text: str) -> dict:
    fields = extract_document_fields(text, "invoice")
    return {
        "invoice_number": fields["invoice_number"] or "AI-DRAFT",
        "issue_date": fields["issue_date"],
        "currency": fields["currency"],
        "subtotal": fields["subtotal"],
        "tax": fields["tax"],
        "total": fields["total"],
        "confidence": fields["confidence"],
    }
