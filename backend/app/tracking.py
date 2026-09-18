from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeviceHistory, IpDeviceShared, LoginSession, User


def upsert_device(db: Session, user_id: UUID, device_id: str, now: datetime) -> DeviceHistory:
    device = db.scalar(
        select(DeviceHistory).where(DeviceHistory.user_id == user_id, DeviceHistory.device_id == device_id)
    )
    if device:
        device.last_seen = now
        device.trust_score = min(100, device.trust_score + 1)
        return device
    device = DeviceHistory(
        user_id=user_id,
        device_id=device_id,
        first_seen=now,
        last_seen=now,
        trust_score=40,
    )
    db.add(device)
    return device


def record_login(db: Session, user_id: UUID, device_id: str, geo: dict) -> LoginSession:
    now = geo.get("login_time") or datetime.now(timezone.utc)
    upsert_device(db, user_id, device_id, now)
    session = LoginSession(
        user_id=user_id,
        device_id=device_id,
        ip_address=geo["ip_address"],
        location_lat=geo.get("lat"),
        location_lng=geo.get("lng"),
        city=geo.get("city"),
        country=geo.get("country"),
        login_time=now,
    )
    db.add(session)
    upsert_share(db, user_id, device_id, geo["ip_address"], now)
    return session


def upsert_share(db: Session, user_id: UUID, device_id: str, ip_address: str, now: datetime) -> None:
    for pending in db.new:
        if (
            isinstance(pending, IpDeviceShared)
            and pending.user_id == user_id
            and pending.device_id == device_id
            and pending.ip_address == ip_address
        ):
            pending.last_seen = now
            return

    row = db.scalar(
        select(IpDeviceShared).where(
            IpDeviceShared.user_id == user_id,
            IpDeviceShared.device_id == device_id,
            IpDeviceShared.ip_address == ip_address,
        )
    )
    if row:
        row.last_seen = now
        return
    db.add(
        IpDeviceShared(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            first_seen=now,
            last_seen=now,
        )
    )


def ensure_profile_shell(db: Session, user: User) -> None:
    """New accounts get an empty trust profile; device/location baselines start empty."""
    _ = user.id
    db.flush()
