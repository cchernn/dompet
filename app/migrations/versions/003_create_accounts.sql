CREATE TABLE IF NOT EXISTS dompet.accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, code)
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_active
    ON dompet.accounts (user_id)
    WHERE is_active = TRUE;
