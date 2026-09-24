CREATE TABLE IF NOT EXISTS dompet.attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(255),
    size_bytes BIGINT,
    storage_key VARCHAR(1024) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attachments_user_id
    ON dompet.attachments (user_id);
