# SentinelPay — AI Fraud Detection System

React + FastAPI + PostgreSQL + FingerprintJS.

## Run locally

1. Start Postgres (preferred):

```bash
docker compose up -d
```

If Docker is not installed, the API automatically falls back to a local SQLite file (`backend/sentinelpay.db`) so you can still demo the full stack. The canonical schema remains PostgreSQL (`backend/schema.sql`).

2. Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py
uvicorn app.main:app --reload --port 8000
```

3. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Demo accounts (password `Demo@123`)

| Email | What you will see |
| --- | --- |
| `priya@sentinelpay.demo` | 20 days of normal Mumbai spend, then a London / new-device ₹50,000 High-risk event |
| `arjun@sentinelpay.demo` `meera@sentinelpay.demo` `vikram@sentinelpay.demo` | Same `device_id` — mule network graph |
| `drift@sentinelpay.demo` | Amounts ramp for 2 weeks (Medium near the end) |

After login the UI immediately calls `GET /account/profile` and fills the dashboard (devices, locations, last transactions, trust score). New accounts show **Building your trust profile…** until 5 scored transactions exist.
