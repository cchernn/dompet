CREATE TABLE IF NOT EXISTS dompet.locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    type VARCHAR(255) NOT NULL
        CHECK (type IN ('physical', 'online')),

    name VARCHAR(255) NOT NULL,

    google_maps_url TEXT,
    url TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        (type = 'physical' AND google_maps_url IS NOT NULL)
        OR
        (type = 'online' AND url IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_locations_active
    ON dompet.locations (id)
    WHERE is_active = TRUE;
