from datetime import date
from pathlib import Path
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
from ..services.ai_extraction import extract_invoice_fields, read_document_text

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
    dest = Path(settings.upload_dir) / file.filename
    dest.write_bytes(file.file.read())
    text = read_document_text(str(dest))
    fields = extract_invoice_fields(text)
    inv = Invoice(invoice_type=invoice_type, invoice_number=fields["invoice_number"], subtotal=fields["subtotal"], total=fields["total"], source_file=str(dest), extracted_text=text)
    db.add(inv); db.commit(); db.refresh(inv)
    return {"invoice": InvoiceRead.model_validate(inv), "extraction": fields}

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

@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    receivables = db.query(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).filter(Invoice.invoice_type == InvoiceType.sales).scalar()
    payables = db.query(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).filter(Invoice.invoice_type == InvoiceType.purchase).scalar()
    overdue = db.query(Invoice).filter(Invoice.due_date < date.today(), Invoice.status != InvoiceStatus.paid).count()
    customers = db.query(Party).filter(Party.type == "customer").count()
    return DashboardMetrics(total_receivables=float(receivables), total_payables=float(payables), overdue_invoices=overdue, open_customers=customers)

@router.get("/reports/aging")
def aging_report(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Invoice).filter(Invoice.status != InvoiceStatus.paid).all()
