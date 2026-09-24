CREATE TABLE IF NOT EXISTS dompet.transaction_budgets (
    transaction_id UUID NOT NULL
        REFERENCES dompet.transactions (id) ON DELETE CASCADE,
    budget_id UUID NOT NULL
        REFERENCES dompet.budgets (id) ON DELETE CASCADE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (transaction_id, budget_id)
);

CREATE INDEX IF NOT EXISTS idx_transaction_budgets_budget_id
    ON dompet.transaction_budgets (budget_id);
