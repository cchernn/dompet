CREATE OR REPLACE VIEW dompet.vw_attachments WITH (security_invoker = true) AS
SELECT
    id, filename, content_type, created_at, size_bytes,
    (
        SELECT COUNT(*) FROM dompet.transaction_attachments ta WHERE ta.attachment_id = attachments.id
    ) AS transaction_count
FROM dompet.attachments
WHERE is_active = TRUE;
