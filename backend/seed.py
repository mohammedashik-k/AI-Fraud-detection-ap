"""Seed demo users, sessions, transactions, and mule-network links."""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import delete, select

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.fraud_engine import calculate_risk
from app.models import DeviceHistory, IpDeviceShared, LoginSession, Transaction, User
from app.tracking import record_login, upsert_device, upsert_share

DEMO_PASSWORD = "Demo@123"
MUMBAI = {"lat": 19.0760, "lng": 72.8777, "city": "Mumbai", "country": "India", "ip": "103.21.244.10"}
DELHI = {"lat": 28.6139, "lng": 77.2090, "city": "Delhi", "country": "India", "ip": "103.21.244.40"}
LONDON = {"lat": 51.5074, "lng": -0.1278, "city": "London", "country": "United Kingdom", "ip": "81.2.69.142"}
DEVICE_A = "fp_priya_laptop"
DEVICE_B = "fp_priya_phone"
DEVICE_NEW = "fp_unknown_browser"
MULE_DEVICE = "fp_mule_shared_android"


def geo_at(place: dict, device_id: str, when: datetime) -> dict:
    return {
        "ip_address": place["ip"],
        "lat": place["lat"],
        "lng": place["lng"],
        "city": place["city"],
        "country": place["country"],
        "login_time": when,
        "device_id": device_id,
    }


def add_txn(db, user_id, amount, category, device_id, place, when, ip=None):
    current = {
        "amount": amount,
        "merchant_category": category,
        "device_id": device_id,
        "ip_address": ip or place["ip"],
        "lat": place["lat"],
        "lng": place["lng"],
        "city": place["city"],
        "country": place["country"],
        "timestamp": when,
    }
    result = calculate_risk(db, user_id, current)
    txn = Transaction(
        user_id=user_id,
        amount=amount,
        merchant_category=category,
        device_id=device_id,
        ip_address=current["ip_address"],
        location_lat=place["lat"],
        location_lng=place["lng"],
        timestamp=when,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        action_taken=result["action"],
        reasoning=result["reasoning"],
    )
    db.add(txn)
    upsert_share(db, user_id, device_id, current["ip_address"], when)
    db.flush()
    return txn


def upsert_user(db, email: str, created_at: datetime) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, password_hash=hash_password(DEMO_PASSWORD), created_at=created_at)
    db.add(user)
    db.flush()
    return user


def reset_demo_data(db):
    emails = {
        "priya@sentinelpay.demo",
        "arjun@sentinelpay.demo",
        "meera@sentinelpay.demo",
        "vikram@sentinelpay.demo",
        "drift@sentinelpay.demo",
    }
    users = db.scalars(select(User).where(User.email.in_(emails))).all()
    ids = [u.id for u in users]
    if not ids:
        return
    db.execute(delete(Transaction).where(Transaction.user_id.in_(ids)))
    db.execute(delete(LoginSession).where(LoginSession.user_id.in_(ids)))
    db.execute(delete(DeviceHistory).where(DeviceHistory.user_id.in_(ids)))
    db.execute(delete(IpDeviceShared).where(IpDeviceShared.user_id.in_(ids)))
    db.execute(delete(User).where(User.id.in_(ids)))
    db.flush()


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    try:
        reset_demo_data(db)

        priya = upsert_user(db, "priya@sentinelpay.demo", now - timedelta(days=40))
        for day in range(20, 0, -1):
            when = now - timedelta(days=day, hours=rng.randint(2, 8))
            device = DEVICE_A if day % 2 == 0 else DEVICE_B
            record_login(db, priya.id, device, geo_at(MUMBAI, device, when))
            amount = rng.randint(500, 3000)
            cats = ["Grocery", "Fuel", "Restaurants", "Utilities", "Online"]
            add_txn(db, priya.id, amount, rng.choice(cats), device, MUMBAI, when + timedelta(minutes=20))
        db.commit()

        # Scenario A: same user, new device + different country minutes later + ₹50,000
        last_login = now - timedelta(minutes=12)
        record_login(db, priya.id, DEVICE_A, geo_at(MUMBAI, DEVICE_A, last_login))
        attack_time = now - timedelta(minutes=4)
        record_login(db, priya.id, DEVICE_NEW, geo_at(LONDON, DEVICE_NEW, attack_time))
        add_txn(db, priya.id, 50000, "Jewelry", DEVICE_NEW, LONDON, attack_time + timedelta(minutes=1))
        db.commit()

        # Scenario B: 3 accounts sharing one device (mule network)
        mule_users = [
            upsert_user(db, "arjun@sentinelpay.demo", now - timedelta(days=12)),
            upsert_user(db, "meera@sentinelpay.demo", now - timedelta(days=9)),
            upsert_user(db, "vikram@sentinelpay.demo", now - timedelta(days=7)),
        ]
        for i, u in enumerate(mule_users):
            when = now - timedelta(hours=6 + i)
            record_login(db, u.id, MULE_DEVICE, geo_at(DELHI, MULE_DEVICE, when))
            add_txn(db, u.id, 8000 + i * 500, "Transfer", MULE_DEVICE, DELHI, when + timedelta(minutes=8))
        db.commit()

        # Scenario C: spend slowly ramps over 2 weeks → Medium near the end
        drift = upsert_user(db, "drift@sentinelpay.demo", now - timedelta(days=20))
        for day in range(14, 0, -1):
            when = now - timedelta(days=day, hours=3)
            record_login(db, drift.id, DEVICE_B, geo_at(MUMBAI, DEVICE_B, when))
            amount = 900 + (14 - day) * 420
            add_txn(db, drift.id, amount, "Electronics", DEVICE_B, MUMBAI, when + timedelta(minutes=30))
        db.commit()

        print("Seed complete. Demo logins (password: Demo@123)")
        print("  Normal + Scenario A: priya@sentinelpay.demo")
        print("  Mule network:        arjun@ / meera@ / vikram@sentinelpay.demo")
        print("  Behavioral drift:    drift@sentinelpay.demo")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
