from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.account import router as account_router
from app.config import settings
from app.database import Base, engine
from app.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SentinelPay", description="AI Fraud Detection System", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(account_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "SentinelPay"}
