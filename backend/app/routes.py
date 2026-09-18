from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account import build_account_profile
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.fraud_engine import calculate_risk
from app.geo import resolve_geo
from app.models import IpDeviceShared, LoginSession, Transaction, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, TransactionRequest
from app.tracking import ensure_profile_shell, record_login, upsert_share

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    ensure_profile_shell(db, user)
    db.commit()
    db.refresh(user)
    return {
        "user_id": str(user.id),
        "email": user.email,
        "account_id": f"SP-{str(user.id).split('-')[0].upper()}",
        "created_at": user.created_at,
        "message": "Account created. Trust profile will build after your first logins and transactions.",
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    geo = resolve_geo(
        request,
        simulate_ip=payload.simulate_ip,
        simulate_lat=payload.simulate_lat,
        simulate_lng=payload.simulate_lng,
        simulate_city=payload.simulate_city,
        simulate_country=payload.simulate_country,
    )
    prior_sessions = db.scalar(
        select(LoginSession).where(LoginSession.user_id == user.id).limit(1)
    )
    is_new = prior_sessions is None
    record_login(db, user.id, payload.device_id, geo)
    db.commit()
    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        is_new_account=is_new,
    )


@router.post("/transaction")
def create_transaction(
    payload: TransactionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    geo = resolve_geo(
        request,
        simulate_ip=payload.simulate_ip,
        simulate_lat=payload.simulate_lat,
        simulate_lng=payload.simulate_lng,
        simulate_city=payload.simulate_city,
        simulate_country=payload.simulate_country,
    )
    latest = db.scalar(
        select(LoginSession)
        .where(LoginSession.user_id == user.id)
        .order_by(LoginSession.login_time.desc())
        .limit(1)
    )
    if latest and not payload.simulate_city and not payload.simulate_country:
        geo["lat"] = latest.location_lat
        geo["lng"] = latest.location_lng
        geo["city"] = latest.city
        geo["country"] = latest.country
        geo["ip_address"] = payload.simulate_ip or latest.ip_address

    now = datetime.now(timezone.utc)
    current = {
        "amount": payload.amount,
        "merchant_category": payload.merchant_category,
        "device_id": payload.device_id,
        "ip_address": geo["ip_address"],
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
        "city": geo.get("city"),
        "country": geo.get("country"),
        "timestamp": now,
    }
    result = calculate_risk(db, user.id, current)
    txn = Transaction(
        user_id=user.id,
        amount=payload.amount,
        merchant_category=payload.merchant_category,
        device_id=payload.device_id,
        ip_address=geo["ip_address"],
        location_lat=geo.get("lat"),
        location_lng=geo.get("lng"),
        timestamp=now,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        action_taken=result["action"],
        reasoning=result["reasoning"],
    )
    db.add(txn)
    upsert_share(db, user.id, payload.device_id, geo["ip_address"], now)
    db.commit()
    db.refresh(txn)
    return {
        "transaction_id": str(txn.id),
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "recommended_action": result["action"],
        "reasoning": result["reasoning"],
        "signals": result.get("signals"),
        "amount": float(txn.amount),
        "merchant_category": txn.merchant_category,
        "timestamp": txn.timestamp,
    }


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_account_profile(db, user)


@router.get("/admin/mule-network")
def mule_network(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(IpDeviceShared)).all()
    users = {str(u.id): u for u in db.scalars(select(User)).all()}

    device_map: dict[str, set[str]] = {}
    ip_map: dict[str, set[str]] = {}
    for row in rows:
        uid = str(row.user_id)
        device_map.setdefault(row.device_id, set()).add(uid)
        ip_map.setdefault(row.ip_address, set()).add(uid)

    nodes = []
    linked_ids: set[str] = set()
    links = []
    seen_edges: set[tuple] = set()

    def add_clique(group: set[str], kind: str, shared_value: str):
        members = sorted(group)
        if len(members) < 2:
            return
        linked_ids.update(members)
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                key = (a, b, kind, shared_value)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                links.append(
                    {
                        "source": a,
                        "target": b,
                        "type": kind,
                        "shared_value": shared_value,
                    }
                )

    for device_id, group in device_map.items():
        add_clique(group, "device", device_id)
    for ip, group in ip_map.items():
        add_clique(group, "ip", ip)

    for uid, u in users.items():
        nodes.append({"id": uid, "email": u.email, "account_id": f"SP-{uid.split('-')[0].upper()}"})

    return {"nodes": nodes, "links": links, "shared_devices": {k: list(v) for k, v in device_map.items() if len(v) > 1}, "shared_ips": {k: list(v) for k, v in ip_map.items() if len(v) > 1}}
