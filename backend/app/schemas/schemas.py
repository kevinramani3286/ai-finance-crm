from datetime import date
from pydantic import BaseModel
from ..models.entities import InvoiceStatus, InvoiceType, ReminderChannel, Role

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserRegister(BaseModel):
    email: str
    full_name: str
    password: str

class UserCreate(UserRegister):
    role: Role = Role.viewer

class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    model_config = {"from_attributes": True}

class PartyBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None

class PartyCreate(PartyBase): pass
class PartyRead(PartyBase):
    id: int
    type: str
    model_config = {"from_attributes": True}

class InvoiceCreate(BaseModel):
    invoice_type: InvoiceType
    invoice_number: str
    party_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    currency: str = "USD"
    subtotal: float = 0
    tax: float = 0
    total: float = 0
    status: InvoiceStatus = InvoiceStatus.draft

class InvoiceRead(InvoiceCreate):
    id: int
    amount_paid: float
    source_file: str | None = None
    extracted_text: str | None = None
    model_config = {"from_attributes": True}

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    paid_at: date | None = None
    method: str | None = None
    reference: str | None = None

class PaymentRead(PaymentCreate):
    id: int
    paid_at: date
    model_config = {"from_attributes": True}

class ReminderCreate(BaseModel):
    invoice_id: int
    channel: ReminderChannel
    recipient: str
    message: str

class DashboardMetrics(BaseModel):
    total_receivables: float
    total_payables: float
    overdue_invoices: int
    open_customers: int
