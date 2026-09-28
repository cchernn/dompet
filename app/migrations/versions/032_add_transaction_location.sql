ALTER TABLE dompet.transactions ADD COLUMN location_id UUID REFERENCES dompet.locations (id);

CREATE INDEX idx_transactions_location_id
    ON dompet.transactions (location_id)
    WHERE location_id IS NOT NULL;
