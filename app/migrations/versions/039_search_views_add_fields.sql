CREATE OR REPLACE VIEW dompet.vw_categories WITH (security_invoker = true) AS
SELECT
    c.id, c.name, c.parent_id,
    (
        SELECT COUNT(*) FROM dompet.transactions t WHERE t.category_id = c.id
    ) AS usage_count,
    c.user_id
FROM dompet.categories c
WHERE c.is_active = TRUE;

CREATE OR REPLACE VIEW dompet.vw_locations WITH (security_invoker = true) AS
SELECT
    l.id, l.name, l.type,
    (
        SELECT COUNT(*) FROM dompet.account_locations al WHERE al.location_id = l.id
    ) AS usage_count,
    l.user_id
FROM dompet.locations l
WHERE l.is_active = TRUE;

CREATE OR REPLACE VIEW dompet.vw_attachments WITH (security_invoker = true) AS
SELECT id, filename, content_type, created_at, size_bytes
FROM dompet.attachments
WHERE is_active = TRUE;
