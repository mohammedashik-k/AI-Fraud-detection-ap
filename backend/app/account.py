from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.fraud_engine import MIN_TXNS_FOR_TRUST, compute_account_trust
from app.models import User

router = APIRouter(prefix="/account", tags=["account"])


def build_account_profile(db: Session, user: User, active_device_id: str | None = None) -> dict:
    profile = compute_account_trust(db, user)
    devices = profile["devices"]
    sessions = profile["sessions"]
    txns = profile["transactions"]
    current = sessions[0] if sessions else None

    device_payload = []
    for d in sorted(devices, key=lambda x: x.last_seen, reverse=True):
        device_payload.append(
            {
                "device_id": d.device_id,
                "first_seen": d.first_seen,
                "last_seen": d.last_seen,
                "device_trust_score": d.trust_score,
                "is_current": bool(
                    (active_device_id and d.device_id == active_device_id)
                    or (current and d.device_id == current.device_id)
                ),
            }
        )

    locations = [
        {
            "city": s.city,
            "country": s.country,
            "ip_address": s.ip_address,
            "device_id": s.device_id,
            "lat": s.location_lat,
            "lng": s.location_lng,
            "timestamp": s.login_time,
            "is_current": current is not None and s.id == current.id,
        }
        for s in sessions[:25]
    ]

    last_five = [
        {
            "id": str(t.id),
            "amount": float(t.amount),
            "merchant_category": t.merchant_category,
            "timestamp": t.timestamp,
            "risk_score": t.risk_score,
            "risk_level": t.risk_level,
            "action_taken": t.action_taken,
            "reasoning": t.reasoning,
        }
        for t in txns[:5]
    ]

    history = [
        {
            "id": str(t.id),
            "amount": float(t.amount),
            "merchant_category": t.merchant_category,
            "device_id": t.device_id,
            "ip_address": t.ip_address,
            "timestamp": t.timestamp,
            "risk_score": t.risk_score,
            "risk_level": t.risk_level,
            "action_taken": t.action_taken,
            "reasoning": t.reasoning,
        }
        for t in txns[:100]
    ]

    return {
        "email": user.email,
        "account_id": f"SP-{str(user.id).split('-')[0].upper()}",
        "user_id": str(user.id),
        "account_created_date": user.created_at,
        "building_trust_profile": profile["building_profile"],
        "trust_score": profile["trust_score"],
        "trust_breakdown": {
            "device_consistency": profile["device_consistency"],
            "location_consistency": profile["location_consistency"],
            "history_cleanliness": profile["history_cleanliness"],
            "age_days": round(profile["age_days"], 1),
        },
        "device_profile": {
            "known_devices": device_payload,
            "active_device_id": current.device_id if current else active_device_id,
        },
        "location_profile": {
            "current_session": {
                "device_id": current.device_id if current else None,
                "ip_address": current.ip_address if current else None,
                "city": current.city if current else None,
                "country": current.country if current else None,
                "lat": current.location_lat if current else None,
                "lng": current.location_lng if current else None,
                "login_time": current.login_time if current else None,
            }
            if current
            else None,
            "past_locations": locations,
        },
        "transaction_profile": {
            "total_transactions": profile["txn_count"],
            "average_transaction_amount": profile["avg_amount"] or 0,
            "last_five": last_five,
            "historical_avg_risk_score": profile["avg_risk"] or 0,
            "history": history,
        },
        "min_txns_for_trust": MIN_TXNS_FOR_TRUST,
        "generated_at": datetime.now(timezone.utc),
    }


@router.get("/profile")
def get_account_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_account_profile(db, user)
