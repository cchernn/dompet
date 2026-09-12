CREATE TABLE IF NOT EXISTS dompet.categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID,

    name VARCHAR(255) NOT NULL,

    parent_id UUID
        REFERENCES dompet.categories (id),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS categories_global_unique
    ON dompet.categories (parent_id, name)
    WHERE user_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS categories_user_unique
    ON dompet.categories (user_id, parent_id, name)
    WHERE user_id IS NOT NULL;
