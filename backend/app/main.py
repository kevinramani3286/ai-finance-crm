from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .config import settings
from .database import Base, engine
from . import models

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AI Finance CRM API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/")
def root(): return {"name": settings.app_name, "status": "running", "version": "1.0.0"}
@app.get("/health")
def health(): return {"status": "ok"}
