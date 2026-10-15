-- Weather BFF schema (mirrors api/app/db.py:ensure_schema for redundancy).

CREATE TABLE IF NOT EXISTS favorites (
    device_id   TEXT NOT NULL,
    id          TEXT NOT NULL,               -- "lat,lon" rounded to 3 dp
    name        TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    admin1      TEXT,
    country     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (device_id, id)
);

CREATE TABLE IF NOT EXISTS search_history (
    id          BIGSERIAL PRIMARY KEY,
    device_id   TEXT NOT NULL,
    name        TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_history_device_time
    ON search_history (device_id, created_at DESC);
