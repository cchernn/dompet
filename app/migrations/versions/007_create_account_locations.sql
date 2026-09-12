CREATE TABLE IF NOT EXISTS dompet.account_locations (
    account_id UUID NOT NULL
        REFERENCES dompet.accounts (id) ON DELETE CASCADE,
    location_id UUID NOT NULL
        REFERENCES dompet.locations (id) ON DELETE CASCADE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (account_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_account_locations_location_id
    ON dompet.account_locations (location_id);
