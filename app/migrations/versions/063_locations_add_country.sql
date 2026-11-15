-- Country for physical locations, stored as an uppercase ISO 3166-1 alpha-2
-- code (e.g. 'MY'). Nullable here so existing rows stay valid until they are
-- backfilled; a follow-up migration makes it required for physical locations.
ALTER TABLE dompet.locations
    ADD COLUMN country VARCHAR(2),
    ADD CONSTRAINT locations_country_format_check CHECK (country IS NULL OR country ~ '^[A-Z]{2}$');

-- CREATE OR REPLACE VIEW can only append columns, so country goes last.
CREATE OR REPLACE VIEW dompet.vw_locations WITH (security_invoker = true) AS
SELECT
    l.id,
    l.name,
    l.type,
    (
        SELECT COUNT(*) FROM dompet.account_locations al WHERE al.location_id = l.id
    ) AS account_count,
    (
        SELECT COUNT(*) FROM dompet.transactions t
        WHERE t.source_location_id = l.id OR t.destination_location_id = l.id
    ) AS transaction_count,
    l.user_id,
    u.username,
    u.display_name,
    l.country
FROM dompet.locations l
LEFT JOIN dompet.vw_users_public u ON u.id = l.user_id
WHERE l.is_active = TRUE;

GRANT SELECT ON dompet.vw_locations TO web_user;
