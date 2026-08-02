# AI Finance CRM ERP

Production-oriented AI finance CRM/ERP scaffold with React + Vite + TypeScript + Tailwind/shadcn-style UI and a FastAPI + SQLAlchemy backend.

## Modules

- JWT authentication and role-based access control
- Dashboard KPIs
- Customers and suppliers
- Sales and purchase invoices
- PDF/image upload with OCR fallback
- AI-assisted invoice field extraction
- Payment tracking
- WhatsApp and email reminder queue
- Reports and invoice aging

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

- API: <http://localhost:8000>
- Frontend: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>

## Backend tests

```bash
cd backend
DATABASE_URL=sqlite:///./test.db PYTHONPATH=. pytest
```
