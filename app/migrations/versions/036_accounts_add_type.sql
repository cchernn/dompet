ALTER TABLE dompet.accounts ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'other'
    CHECK (type IN ('bank', 'wallet', 'merchant', 'online', 'utility', 'subscription', 'other'));
