from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import atan2, cos, radians, sin, sqrt
from statistics import mean, pstdev
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DeviceHistory, IpDeviceShared, LoginSession, Transaction, User

MIN_TXNS_FOR_TRUST = 5
NEW_ACCOUNT_BASELINE = 8
HIGH_TRUST_DISCOUNT = 0.85


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_account_trust(db: Session, user: User) -> dict:
    now = datetime.now(timezone.utc)
    devices = db.scalars(select(DeviceHistory).where(DeviceHistory.user_id == user.id)).all()
    sessions = db.scalars(
        select(LoginSession).where(LoginSession.user_id == user.id).order_by(LoginSession.login_time.desc())
    ).all()
    txns = db.scalars(
        select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.timestamp.desc())
    ).all()

    txn_count = len(txns)
    building_profile = txn_count < MIN_TXNS_FOR_TRUST
    age_days = max((now - _aware(user.created_at)).total_seconds() / 86400, 0)

    device_consistency = 100
    if devices:
        unique = len(devices)
        device_consistency = max(20, 100 - (unique - 1) * 18)

    location_consistency = 100
    countries = {s.country for s in sessions if s.country}
    if countries:
        location_consistency = max(15, 100 - (len(countries) - 1) * 22)

    if txn_count == 0:
        history_cleanliness = 55
        avg_risk = None
        avg_amount = None
    else:
        scores = [t.risk_score for t in txns]
        avg_risk = round(mean(scores), 2)
        avg_amount = round(float(mean([float(t.amount) for t in txns])), 2)
        high_ratio = sum(1 for t in txns if t.risk_level == "High") / txn_count
        history_cleanliness = max(10, 100 - avg_risk * 0.7 - high_ratio * 40)

    if building_profile:
        trust = round(
            0.25 * device_consistency + 0.25 * location_consistency + 0.20 * history_cleanliness + 0.30 * 45
        )
        trust = min(trust, 58)
    else:
        longevity = min(100, 40 + age_days * 3)
        trust = round(
            0.30 * device_consistency
            + 0.25 * location_consistency
            + 0.35 * history_cleanliness
            + 0.10 * longevity
        )

    trust = int(max(5, min(100, trust)))
    return {
        "trust_score": trust,
        "building_profile": building_profile,
        "txn_count": txn_count,
        "avg_risk": avg_risk,
        "avg_amount": avg_amount,
        "age_days": age_days,
        "device_consistency": round(device_consistency),
        "location_consistency": round(location_consistency),
        "history_cleanliness": round(history_cleanliness),
        "devices": devices,
        "sessions": sessions,
        "transactions": txns,
    }


def _sharing_other_accounts(db: Session, user_id: UUID, device_id: str, ip_address: str) -> int:
    device_users = db.scalars(
        select(IpDeviceShared.user_id).where(IpDeviceShared.device_id == device_id).distinct()
    ).all()
    ip_users = db.scalars(
        select(IpDeviceShared.user_id).where(IpDeviceShared.ip_address == ip_address).distinct()
    ).all()
    others = {u for u in device_users + ip_users if str(u) != str(user_id)}
    return len(others)


def calculate_risk(db: Session, user_id: UUID, current_transaction: dict) -> dict:
    """Score a transaction. current_transaction keys: amount, merchant_category, device_id, ip_address, lat, lng, city, country, timestamp."""
    user = db.get(User, user_id)
    if not user:
        return {
            "risk_score": 70,
            "risk_level": "High",
            "action": "Block + Escalate to Review",
            "reasoning": "Unknown account. Transaction blocked pending identity verification.",
        }

    now = _aware(current_transaction.get("timestamp")) or datetime.now(timezone.utc)
    amount = float(current_transaction["amount"])
    device_id = current_transaction["device_id"]
    ip_address = current_transaction.get("ip_address") or "0.0.0.0"
    lat = current_transaction.get("lat")
    lng = current_transaction.get("lng")
    city = current_transaction.get("city")
    country = current_transaction.get("country")

    profile = compute_account_trust(db, user)
    devices = profile["devices"]
    sessions = profile["sessions"]
    txns = profile["transactions"]

    score = 0
    reasons: list[str] = []
    new_device = False
    new_location = False
    high_amount = False

    known_ids = {d.device_id for d in devices}
    if device_id not in known_ids:
        new_device = True
        score += 25
        reasons.append("New device detected.")
    else:
        reasons.append("Recognized device on this account.")

    last_session = sessions[0] if sessions else None
    if last_session and lat is not None and lng is not None and last_session.location_lat is not None and last_session.location_lng is not None:
        distance = haversine_km(last_session.location_lat, last_session.location_lng, lat, lng)
        elapsed_h = max((now - _aware(last_session.login_time)).total_seconds() / 3600, 1 / 3600)
        speed = distance / elapsed_h
        minutes = max(int((now - _aware(last_session.login_time)).total_seconds() / 60), 1)
        if distance > 150:
            new_location = True
        if speed > 900:
            score += 40
            reasons.append(
                f"Impossible Travel: login location {distance:.0f}km from previous session "
                f"({last_session.city or 'unknown'}, {last_session.country or 'unknown'}) within {minutes} minutes "
                f"(implied {speed:.0f} km/h)."
            )
        elif last_session.country and country and last_session.country != country:
            new_location = True
            score += 18
            reasons.append(
                f"Location jumped from {last_session.city or last_session.country} to {city or country} "
                f"({distance:.0f}km apart)."
            )
        elif distance > 400:
            new_location = True
            score += 12
            reasons.append(f"Login location {distance:.0f}km from previous session.")
    elif country and last_session and last_session.country and country != last_session.country:
        new_location = True
        score += 18
        reasons.append(f"Country changed from {last_session.country} to {country}.")

    other_accounts = _sharing_other_accounts(db, user_id, device_id, ip_address)
    if other_accounts >= 2:
        score += 35
        reasons.append(
            f"Mule network signal: this device or IP is linked to {other_accounts} other user accounts."
        )
    elif other_accounts == 1:
        score += 12
        reasons.append("This device or IP is also linked to another user account.")

    window_30 = now - timedelta(days=30)
    recent_amounts = [float(t.amount) for t in txns if _aware(t.timestamp) >= window_30]
    if len(recent_amounts) >= 3:
        avg = mean(recent_amounts)
        std = pstdev(recent_amounts) if len(recent_amounts) > 1 else 0.0
        threshold = avg + 2 * std
        if amount > threshold and (std > 0 or amount > avg * 2):
            high_amount = True
            score += 20
            multiple = amount / avg if avg else amount
            reasons.append(
                f"Amount ₹{amount:,.0f} is {multiple:.1f}x your 30-day average (₹{avg:,.0f})."
            )
        elif amount > avg * 3:
            high_amount = True
            score += 20
            reasons.append(f"Amount ₹{amount:,.0f} is far above your 30-day average of ₹{avg:,.0f}.")
    elif amount >= 20000:
        high_amount = True
        score += 16
        reasons.append("High-value transaction on an account with limited spend history.")

    last_10m = sum(1 for t in txns if _aware(t.timestamp) >= now - timedelta(minutes=10))
    last_24h = sum(1 for t in txns if _aware(t.timestamp) >= now - timedelta(hours=24))
    older = [t for t in txns if _aware(t.timestamp) < now - timedelta(hours=24)]
    daily_norm = 2.0
    if older:
        first = _aware(older[-1].timestamp) or now
        span_days = max((now - first).total_seconds() / 86400, 1)
        daily_norm = max(len(older) / span_days, 1)

    unusual_velocity = last_10m >= 3 or last_24h > max(4, daily_norm * 3)
    if unusual_velocity:
        score += 15
        reasons.append(
            f"Unusual velocity: {last_10m} transaction(s) in 10 minutes and {last_24h} in 24 hours "
            f"(typical daily volume ≈ {daily_norm:.1f})."
        )

    if profile["building_profile"]:
        score += NEW_ACCOUNT_BASELINE
        reasons.append(
            "New account baseline: trust profile is still forming, so scoring is slightly stricter."
        )

    if new_device and new_location and high_amount:
        score = round(score * 1.5)
        reasons.append(
            "Compounding risk: new device, new location, and high amount occurred together (1.5x multiplier)."
        )

    high_trust = (
        not profile["building_profile"]
        and profile["trust_score"] >= 75
        and profile["age_days"] >= 14
        and profile["txn_count"] >= MIN_TXNS_FOR_TRUST
    )
    if high_trust and score > 0:
        before = score
        score = round(score * HIGH_TRUST_DISCOUNT)
        reasons.append(
            f"Established account tolerance applied (trust {profile['trust_score']}/100); "
            f"score adjusted {before} → {score}."
        )

    score = int(max(0, min(100, score)))
    if score <= 30:
        level, action = "Safe", "Allow"
    elif score <= 60:
        level, action = "Medium", "Verify with OTP"
    else:
        level, action = "High", "Block + Escalate to Review"

    if not reasons:
        reasons.append("No elevated fraud signals on this transaction.")

    return {
        "risk_score": score,
        "risk_level": level,
        "action": action,
        "reasoning": " ".join(reasons),
        "signals": {
            "new_device": new_device,
            "new_location": new_location,
            "high_amount": high_amount,
            "shared_other_accounts": other_accounts,
            "building_profile": profile["building_profile"],
            "account_trust": profile["trust_score"],
        },
    }
