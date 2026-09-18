from datetime import datetime, timezone

import httpx
from fastapi import Request

from app.config import settings

PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "172.16.", "::1", "localhost")


def client_ip(request: Request, simulate_ip: str | None = None) -> str:
    if simulate_ip:
        return simulate_ip
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _is_private(ip: str) -> bool:
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES)


def geolocate_ip(ip: str) -> dict:
    if _is_private(ip):
        return {
            "ip_address": ip,
            "lat": 19.0760,
            "lng": 72.8777,
            "city": "Mumbai",
            "country": "India",
        }
    try:
        url = f"{settings.ipapi_base_url}/{ip}/json/"
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(url)
            data = resp.json()
        if data.get("error"):
            raise ValueError(data.get("reason", "geo lookup failed"))
        return {
            "ip_address": ip,
            "lat": data.get("latitude"),
            "lng": data.get("longitude"),
            "city": data.get("city") or "Unknown",
            "country": data.get("country_name") or data.get("country") or "Unknown",
        }
    except Exception:
        return {
            "ip_address": ip,
            "lat": None,
            "lng": None,
            "city": "Unknown",
            "country": "Unknown",
        }


def resolve_geo(
    request: Request,
    simulate_ip: str | None = None,
    simulate_lat: float | None = None,
    simulate_lng: float | None = None,
    simulate_city: str | None = None,
    simulate_country: str | None = None,
) -> dict:
    ip = client_ip(request, simulate_ip)
    geo = geolocate_ip(ip)
    if simulate_lat is not None:
        geo["lat"] = simulate_lat
    if simulate_lng is not None:
        geo["lng"] = simulate_lng
    if simulate_city:
        geo["city"] = simulate_city
    if simulate_country:
        geo["country"] = simulate_country
    geo["ip_address"] = ip
    geo["login_time"] = datetime.now(timezone.utc)
    return geo
