CREATE TABLE IF NOT EXISTS dompet.budget_members (
    budget_id UUID NOT NULL
        REFERENCES dompet.budgets (id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (budget_id, user_id)
);
