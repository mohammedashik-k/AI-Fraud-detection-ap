-- SentinelPay PostgreSQL schema
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trust_score INTEGER NOT NULL DEFAULT 50,
    UNIQUE (user_id, device_id)
);

CREATE TABLE IF NOT EXISTS login_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    location_lat DOUBLE PRECISION,
    location_lng DOUBLE PRECISION,
    city VARCHAR(128),
    country VARCHAR(128),
    login_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(14, 2) NOT NULL,
    merchant_category VARCHAR(64) NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    location_lat DOUBLE PRECISION,
    location_lng DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    risk_score INTEGER NOT NULL,
    risk_level VARCHAR(16) NOT NULL,
    action_taken VARCHAR(64) NOT NULL,
    reasoning TEXT NOT NULL
);

-- Tracks which devices/IPs are linked to user accounts (mule network detection)
CREATE TABLE IF NOT EXISTS ip_device_shared (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, device_id, ip_address)
);

CREATE INDEX IF NOT EXISTS idx_device_history_user ON device_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_sessions_user_time ON login_sessions(user_id, login_time DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_user_time ON transactions(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ip_device_shared_device ON ip_device_shared(device_id);
CREATE INDEX IF NOT EXISTS idx_ip_device_shared_ip ON ip_device_shared(ip_address);
