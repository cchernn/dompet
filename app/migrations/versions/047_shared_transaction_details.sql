-- SECURITY DEFINER helpers bypass RLS, so each one gates its own rows on
-- budget membership of the caller (app.current_user_id). They return only
-- what a budget member needs to see a shared transaction.

CREATE OR REPLACE FUNCTION dompet.shared_transaction_details(tx_id uuid)
RETURNS TABLE (
    source text,
    destination text,
    category text,
    source_location text,
    destination_location text,
    attachments json
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
                SELECT json_agg(json_build_object('id', a.id, 'filename', a.filename) ORDER BY a.filename)
                FROM dompet.transaction_attachments ta
                JOIN dompet.attachments a ON a.id = ta.attachment_id
                WHERE ta.transaction_id = t.id AND a.is_active
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

CREATE OR REPLACE FUNCTION dompet.shared_attachment(att_id uuid)
RETURNS SETOF dompet.attachments
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT a.*
    FROM dompet.attachments a
    WHERE a.id = att_id
      AND a.is_active
      AND EXISTS (
          SELECT 1
          FROM dompet.transaction_attachments ta
          JOIN dompet.transactions t ON t.id = ta.transaction_id AND t.is_active
          JOIN dompet.transaction_budgets tb ON tb.transaction_id = t.id
          JOIN dompet.budget_members bm ON bm.budget_id = tb.budget_id
          WHERE ta.attachment_id = a.id
            AND bm.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
      );
$$;

REVOKE ALL ON FUNCTION dompet.shared_transaction_details(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.shared_transaction_details(uuid) TO web_user;

REVOKE ALL ON FUNCTION dompet.shared_attachment(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.shared_attachment(uuid) TO web_user;

-- Rebuilt rather than CREATE OR REPLACE: source/destination/category change type.
DROP VIEW IF EXISTS dompet.vw_transactions;

CREATE VIEW dompet.vw_transactions WITH (security_invoker = true) AS
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
            SELECT json_agg(json_build_object('id', att.id, 'filename', att.filename) ORDER BY att.filename)
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
    t.datetime,
    COALESCE(src_loc.name, sh.source_location) AS source_location,
    COALESCE(dst_loc.name, sh.destination_location) AS destination_location,
    t.user_id
FROM dompet.transactions t
LEFT JOIN dompet.categories c ON c.id = t.category_id
LEFT JOIN dompet.accounts src ON src.id = t.source_account_id
LEFT JOIN dompet.accounts dst ON dst.id = t.destination_account_id
LEFT JOIN dompet.locations src_loc ON src_loc.id = t.source_location_id
LEFT JOIN dompet.locations dst_loc ON dst_loc.id = t.destination_location_id
LEFT JOIN LATERAL dompet.shared_transaction_details(t.id) sh ON TRUE
WHERE t.is_active = TRUE;

GRANT SELECT ON dompet.vw_transactions TO web_user;
