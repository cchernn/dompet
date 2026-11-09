-- Attachments gain a user-given display name, separate from filename.
-- filename (and the storage_key derived from it at upload time) stays
-- exactly as-is -- it's what's actually stored in S3 and never changes.
-- name is purely a dashboard-facing label, defaulting to filename when
-- not given and editable independently afterward.
--
-- Every attachment reference surfaced elsewhere (vw_transactions,
-- shared_transaction_details, vw_attachments) gets 'name' added
-- alongside 'filename' so the dashboard can show the display name while
-- still knowing the underlying file. None of these changes alter an
-- existing output column's type, so CREATE OR REPLACE is safe throughout
-- -- no DROP needed, unlike 052/055's function-signature changes.

ALTER TABLE dompet.attachments ADD COLUMN IF NOT EXISTS name VARCHAR(255);

UPDATE dompet.attachments SET name = filename WHERE name IS NULL;

ALTER TABLE dompet.attachments ALTER COLUMN name SET NOT NULL;

CREATE OR REPLACE VIEW dompet.vw_attachments WITH (security_invoker = true) AS
SELECT
    id, filename, content_type, created_at, size_bytes,
    (
        SELECT COUNT(*) FROM dompet.transaction_attachments ta WHERE ta.attachment_id = attachments.id
    ) AS transaction_count,
    name
FROM dompet.attachments
WHERE is_active = TRUE;

GRANT SELECT ON dompet.vw_attachments TO web_user;

CREATE OR REPLACE FUNCTION dompet.shared_transaction_details(tx_id uuid)
RETURNS TABLE (
    source text,
    destination text,
    category text,
    source_location text,
    destination_location text,
    attachments json,
    bills text[],
    bill_attachments json
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT
        src.name::text,
        dst.name::text,
        c.name::text,
        sl.name::text,
        dl.name::text,
        COALESCE(
            (
                SELECT json_agg(json_build_object('id', a.id, 'filename', a.filename, 'name', a.name) ORDER BY a.name)
                FROM dompet.transaction_attachments ta
                JOIN dompet.attachments a ON a.id = ta.attachment_id
                WHERE ta.transaction_id = t.id AND a.is_active
            ),
            '[]'::json
        ),
        ARRAY(
            SELECT bl.name
            FROM dompet.bill_payments bp
            JOIN dompet.bills bl ON bl.id = bp.bill_id
            WHERE bp.transaction_id = t.id
            ORDER BY bl.name
        ),
        COALESCE(
            (
                SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename, 'name', att.name) ORDER BY att.name)
                FROM dompet.bill_payments bp
                JOIN dompet.bill_attachments ba ON ba.bill_id = bp.bill_id
                JOIN dompet.attachments att ON att.id = ba.attachment_id
                WHERE bp.transaction_id = t.id AND att.is_active
            ),
            '[]'::json
        )
    FROM dompet.transactions t
    LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
    LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
    LEFT JOIN dompet.categories c ON c.id = t.category_id
    LEFT JOIN dompet.locations sl ON sl.id = t.source_location_id
    LEFT JOIN dompet.locations dl ON dl.id = t.destination_location_id
    WHERE t.id = tx_id
      AND t.is_active
      AND t.user_id <> NULLIF(current_setting('app.current_user_id', true), '')::uuid
      AND EXISTS (
          SELECT 1
          FROM dompet.transaction_budgets tb
          JOIN dompet.budget_members bm ON bm.budget_id = tb.budget_id
          WHERE tb.transaction_id = t.id
            AND bm.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
      );
$$;

REVOKE ALL ON FUNCTION dompet.shared_transaction_details(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.shared_transaction_details(uuid) TO web_user;

CREATE OR REPLACE VIEW dompet.vw_transactions WITH (security_invoker = true) AS
SELECT
    t.id,
    t.datetime::date AS date,
    t.name,
    t.type,
    t.amount,
    t.currency_code AS currency,
    COALESCE(c.name, sh.category) AS category,
    COALESCE(src.name, sh.source) AS source,
    COALESCE(dst.name, sh.destination) AS destination,
    ARRAY(
        SELECT tag.name
        FROM dompet.transaction_tags tt
        JOIN dompet.tags tag ON tag.id = tt.tag_id
        WHERE tt.transaction_id = t.id
        ORDER BY tag.name
    ) AS tags,
    COALESCE(
        (
            SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename, 'name', att.name) ORDER BY att.name)
            FROM dompet.transaction_attachments ta
            JOIN dompet.attachments att ON att.id = ta.attachment_id
            WHERE ta.transaction_id = t.id
        ),
        sh.attachments,
        '[]'::json
    ) AS attachments,
    ARRAY(
        SELECT b.name
        FROM dompet.transaction_budgets tb
        JOIN dompet.budgets b ON b.id = tb.budget_id
        WHERE tb.transaction_id = t.id
        ORDER BY b.name
    ) AS budgets,
    (
        ARRAY(
            SELECT bl.name
            FROM dompet.bill_payments bp
            JOIN dompet.bills bl ON bl.id = bp.bill_id
            WHERE bp.transaction_id = t.id
            ORDER BY bl.name
        ) || COALESCE(sh.bills, ARRAY[]::text[])
    ) AS bills,
    COALESCE(
        (
            SELECT json_agg(x) FROM (
                SELECT json_build_object('id', att.id, 'filename', att.filename, 'name', att.name) AS x
                FROM dompet.bill_payments bp
                JOIN dompet.bill_attachments ba ON ba.bill_id = bp.bill_id
                JOIN dompet.attachments att ON att.id = ba.attachment_id
                WHERE bp.transaction_id = t.id
                UNION ALL
                SELECT json_array_elements(sh.bill_attachments)
            ) combined
        ),
        '[]'::json
    ) AS bill_attachments,
    t.datetime,
    COALESCE(src_loc.name, sh.source_location) AS source_location,
    COALESCE(dst_loc.name, sh.destination_location) AS destination_location,
    t.user_id,
    u.username,
    u.display_name
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
LEFT JOIN dompet.locations src_loc ON src_loc.id = t.source_location_id
LEFT JOIN dompet.locations dst_loc ON dst_loc.id = t.destination_location_id
LEFT JOIN LATERAL dompet.shared_transaction_details(t.id) sh ON TRUE
LEFT JOIN dompet.vw_users_public u ON u.id = t.user_id
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transactions TO web_user;
