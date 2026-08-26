from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..api.deps import current_user, require_roles
from ..config import settings
from ..core.security import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models.entities import Invoice, InvoiceStatus, InvoiceType, Party, Payment, Reminder, Role, User
from ..schemas.schemas import *
from ..services.ai_extraction import extract_document_fields, extract_invoice_fields, read_document_text

router = APIRouter(prefix="/api")

@router.post("/auth/register", response_model=UserRead)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password), role=payload.role)
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=create_access_token(user.email, user.role.value))

@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(current_user)): return user

def create_party(kind: str, payload: PartyCreate, db: Session):
    party = Party(type=kind, **payload.model_dump())
    db.add(party); db.commit(); db.refresh(party)
    return party

@router.get("/customers", response_model=list[PartyRead])
def customers(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Party).filter(Party.type == "customer").all()

@router.post("/customers", response_model=PartyRead)
def add_customer(payload: PartyCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.sales, Role.finance))):
    return create_party("customer", payload, db)

@router.get("/suppliers", response_model=list[PartyRead])
def suppliers(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Party).filter(Party.type == "supplier").all()

@router.post("/suppliers", response_model=PartyRead)
def add_supplier(payload: PartyCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.finance))):
    return create_party("supplier", payload, db)

@router.get("/invoices", response_model=list[InvoiceRead])
def invoices(invoice_type: InvoiceType | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Invoice)
    return q.filter(Invoice.invoice_type == invoice_type).all() if invoice_type else q.all()

@router.post("/invoices", response_model=InvoiceRead)
def add_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.finance, Role.sales))):
    inv = Invoice(**payload.model_dump())
    db.add(inv); db.commit(); db.refresh(inv)
    return inv

@router.post("/invoices/upload")
def upload_invoice(invoice_type: InvoiceType, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.finance))):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "document.pdf").suffix.lower()
    dest = Path(settings.upload_dir) / f"{uuid4().hex}{suffix}"
    dest.write_bytes(file.file.read())
    text = read_document_text(str(dest))
    fields = extract_invoice_fields(text)
    inv = Invoice(invoice_type=invoice_type, invoice_number=fields["invoice_number"], subtotal=fields["subtotal"], total=fields["total"], source_file=str(dest), extracted_text=text)
    db.add(inv); db.commit(); db.refresh(inv)
    return {"invoice": InvoiceRead.model_validate(inv), "extraction": fields}

@router.post("/ocr/analyze")
def analyze_document(document_type: str = "invoice", file: UploadFile = File(...)):
    """Universal OCR entry point used by invoice, payment, purchase, bank, quotation and expense screens."""
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "document.pdf").suffix.lower()
    dest = Path(settings.upload_dir) / f"ocr-{uuid4().hex}{suffix}"
    dest.write_bytes(file.file.read())
    text = read_document_text(str(dest))
    fields = extract_document_fields(text, document_type)
    return {
        "file_name": file.filename,
        "document_type": document_type,
        "status": "review" if fields["confidence"] < 0.80 else "ready",
        "confidence": fields["confidence"],
        "fields": fields,
        "text_preview": text[:4000],
    }

@router.post("/payments", response_model=PaymentRead)
def add_payment(payload: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.finance))):
    invoice = db.get(Invoice, payload.invoice_id)
    if not invoice: raise HTTPException(404, "Invoice not found")
    payment = Payment(**payload.model_dump(exclude_none=True))
    invoice.amount_paid = float(invoice.amount_paid or 0) + payload.amount
    invoice.status = InvoiceStatus.paid if invoice.amount_paid >= invoice.total else InvoiceStatus.partially_paid
    db.add(payment); db.commit(); db.refresh(payment)
    return payment

@router.post("/reminders")
def queue_reminder(payload: ReminderCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.finance, Role.sales))):
    reminder = Reminder(**payload.model_dump())
    db.add(reminder); db.commit(); db.refresh(reminder)
    return {"id": reminder.id, "status": reminder.status}

def get_dashboard_metrics(db: Session) -> DashboardMetrics:
    receivables = db.query(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).filter(Invoice.invoice_type == InvoiceType.sales).scalar()
    payables = db.query(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).filter(Invoice.invoice_type == InvoiceType.purchase).scalar()
    overdue = db.query(Invoice).filter(Invoice.due_date < date.today(), Invoice.status != InvoiceStatus.paid).count()
    customers = db.query(Party).filter(Party.type == "customer").count()
    return DashboardMetrics(total_receivables=float(receivables), total_payables=float(payables), overdue_invoices=overdue, open_customers=customers)

@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return get_dashboard_metrics(db)

@router.get("/live-metrics", response_model=DashboardMetrics)
def live_metrics(db: Session = Depends(get_db)):
    return get_dashboard_metrics(db)

@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    fiscal_start_year = today.year if today.month >= 4 else today.year - 1
    fy_start = date(fiscal_start_year, 4, 1)
    fy_end = date(fiscal_start_year + 1, 3, 31)

    sales = db.query(Invoice).filter(Invoice.invoice_type == InvoiceType.sales, Invoice.issue_date >= fy_start, Invoice.issue_date <= fy_end).all()
    purchases = db.query(Invoice).filter(Invoice.invoice_type == InvoiceType.purchase, Invoice.issue_date >= fy_start, Invoice.issue_date <= fy_end).all()
    collections = db.query(Payment).filter(Payment.paid_at >= fy_start, Payment.paid_at <= fy_end).all()
    total_sales = sum(float(x.total or 0) for x in sales)
    total_purchase = sum(float(x.total or 0) for x in purchases)
    total_collections = sum(float(x.amount or 0) for x in collections)
    outstanding = sum(max(0, float(x.total or 0) - float(x.amount_paid or 0)) for x in sales)
    overdue_amount = sum(max(0, float(x.total or 0) - float(x.amount_paid or 0)) for x in sales if x.due_date and x.due_date < today and x.status != InvoiceStatus.paid)

    aging = {"0-7": 0.0, "8-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    open_sales = [x for x in sales if x.status != InvoiceStatus.paid]
    for inv in open_sales:
        age = max(0, (today - (inv.due_date or today)).days)
        amount = max(0, float(inv.total or 0) - float(inv.amount_paid or 0))
        if age <= 7: aging["0-7"] += amount
        elif age <= 30: aging["8-30"] += amount
        elif age <= 60: aging["31-60"] += amount
        elif age <= 90: aging["61-90"] += amount
        else: aging["90+"] += amount

    top = []
    by_party = {}
    for inv in open_sales:
        name = inv.party.name if inv.party else "Unassigned customer"
        by_party[name] = by_party.get(name, 0.0) + max(0, float(inv.total or 0) - float(inv.amount_paid or 0))
    for name, amount in sorted(by_party.items(), key=lambda x: x[1], reverse=True)[:5]:
        top.append({"name": name, "amount": round(amount, 2)})

    payment_modes = {}
    for p in collections:
        key = p.method or "Other"
        payment_modes[key] = payment_modes.get(key, 0.0) + float(p.amount or 0)

    months = []
    cursor = fy_start
    for i in range(12):
        month = cursor.month
        year = cursor.year
        next_month = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        sales_value = sum(float(x.total or 0) for x in sales if x.issue_date and date(x.issue_date.year, x.issue_date.month, 1) == date(year, month, 1))
        collected_value = sum(float(x.amount or 0) for x in collections if x.paid_at and date(x.paid_at.year, x.paid_at.month, 1) == date(year, month, 1))
        months.append({"label": cursor.strftime("%b"), "sales": round(sales_value, 2), "collections": round(collected_value, 2)})
        cursor = next_month

    return {
        "financial_year": f"FY {fiscal_start_year}-{str(fiscal_start_year + 1)[-2:]}",
        "total_sales": round(total_sales, 2),
        "total_collections": round(total_collections, 2),
        "outstanding": round(outstanding, 2),
        "overdue": round(overdue_amount, 2),
        "profit": round(total_sales - total_purchase, 2),
        "expenses": 0.0,
        "aging": aging,
        "top_customers": top,
        "payment_modes": payment_modes,
        "trend": months,
        "invoice_count": len(sales),
        "payments_count": len(collections),
    }

@router.get("/reports/aging")
def aging_report(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Invoice).filter(Invoice.status != InvoiceStatus.paid).all()
