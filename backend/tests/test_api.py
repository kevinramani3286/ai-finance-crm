import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordRequestForm
from app.api.routes import add_customer, add_invoice, add_payment, dashboard, login, register
from app.main import app
from app.database import Base, SessionLocal, engine
from app.models.entities import Role
from app.schemas.schemas import InvoiceCreate, PartyCreate, PaymentCreate, UserCreate


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_auth_and_dashboard_direct_api():
    db = next(db_session())
    user = register(UserCreate(email="admin@example.com", full_name="Admin", password="secret123", role=Role.admin), db)
    form = OAuth2PasswordRequestForm(username="admin@example.com", password="secret123", scope="", client_id=None, client_secret=None)
    token = login(form, db)
    assert token.access_token
    metrics = dashboard(db, user)
    assert metrics.total_receivables == 0


def test_customer_invoice_payment_flow_direct_api():
    db = next(db_session())
    user = register(UserCreate(email="finance@example.com", full_name="Finance", password="secret123", role=Role.finance), db)
    customer = add_customer(PartyCreate(name="Acme", email="ap@acme.com"), db, user)
    invoice = add_invoice(InvoiceCreate(invoice_type="sales", invoice_number="INV-1", party_id=customer.id, total=100), db, user)
    payment = add_payment(PaymentCreate(invoice_id=invoice.id, amount=100, method="bank"), db, user)
    assert payment.id
    db.refresh(invoice)
    assert invoice.status == "paid"


def test_invalid_login_rejected():
    db = next(db_session())
    form = OAuth2PasswordRequestForm(username="none@example.com", password="bad", scope="", client_id=None, client_secret=None)
    try:
        login(form, db)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("invalid login should fail")


def test_live_metrics_requires_auth():
    client = TestClient(app)
    response = client.get("/api/live-metrics")
    assert response.status_code == 401

    db = next(db_session())
    register(UserCreate(email="metrics@example.com", full_name="Metrics", password="secret123", role=Role.finance), db)
    login_response = client.post(
        "/api/auth/login",
        data={"username": "metrics@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    authed_response = client.get("/api/live-metrics", headers={"Authorization": f"Bearer {token}"})
    assert authed_response.status_code == 200
    assert authed_response.json()["total_receivables"] == 0
