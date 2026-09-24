CREATE TABLE IF NOT EXISTS dompet.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    date DATE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL DEFAULT 'expenditure'
        CHECK (type IN ('expenditure', 'income', 'transfer')),
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00
        CHECK (amount >= 0),
    currency_code CHAR(3) NOT NULL
        REFERENCES dompet.currencies (code),
    category_id UUID
        REFERENCES dompet.categories (id),
    source_account_id UUID NOT NULL
        REFERENCES dompet.accounts (id),
    destination_account_id UUID NOT NULL
        REFERENCES dompet.accounts (id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date
    ON dompet.transactions (user_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_user_active
    ON dompet.transactions (user_id)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_transactions_currency_code
    ON dompet.transactions (currency_code);

CREATE INDEX IF NOT EXISTS idx_transactions_category_id
    ON dompet.transactions (category_id)
    WHERE category_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_source_account_id
    ON dompet.transactions (source_account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_destination_account_id
    ON dompet.transactions (destination_account_id);
