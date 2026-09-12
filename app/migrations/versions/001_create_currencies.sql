CREATE TABLE IF NOT EXISTS dompet.currencies (
    code CHAR(3) PRIMARY KEY,

    name VARCHAR(255) NOT NULL,

    symbol VARCHAR(16) NOT NULL,

    decimal_places SMALLINT NOT NULL DEFAULT 2
        CHECK (decimal_places BETWEEN 0 AND 10),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_currencies_active
    ON dompet.currencies (code)
    WHERE is_active = TRUE;
