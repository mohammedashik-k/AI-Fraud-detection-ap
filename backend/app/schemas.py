from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str
    simulate_ip: Optional[str] = None
    simulate_lat: Optional[float] = None
    simulate_lng: Optional[float] = None
    simulate_city: Optional[str] = None
    simulate_country: Optional[str] = None


class TransactionRequest(BaseModel):
    amount: float = Field(gt=0)
    merchant_category: str
    device_id: str
    simulate_ip: Optional[str] = None
    simulate_lat: Optional[float] = None
    simulate_lng: Optional[float] = None
    simulate_city: Optional[str] = None
    simulate_country: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    is_new_account: bool = False


class GeoContext(BaseModel):
    ip_address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    login_time: Optional[datetime] = None
