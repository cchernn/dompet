-- Every search view that surfaces a user_id now also resolves it to a
-- username/display_name via vw_users_public (already a public directory --
-- see 048_create_users.sql -- so a plain LEFT JOIN is enough here, unlike
-- shared_transaction_details's SECURITY DEFINER trick, which exists only
-- because categories/accounts/locations are NOT publicly readable).
-- CREATE OR REPLACE is safe here: these only append trailing columns, never
-- change or remove an existing one. Bodies otherwise copied verbatim from
-- the views' current live definitions (pg_get_viewdef), not re-derived
-- from the original CREATE migrations, since several since-added columns
-- (account_count/transaction_count on locations, shared_transaction_details
-- on transactions) aren't present in those older files.

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

CREATE OR REPLACE VIEW dompet.vw_categories WITH (security_invoker = true) AS
SELECT
    c.id,
    c.name,
    c.parent_id,
    (
        SELECT COUNT(*) FROM dompet.transactions t WHERE t.category_id = c.id
    ) AS transaction_count,
    c.user_id,
    u.username,
    u.display_name
FROM dompet.categories c
LEFT JOIN dompet.vw_users_public u ON u.id = c.user_id
WHERE c.is_active = TRUE;

GRANT SELECT ON dompet.vw_categories TO web_user;

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
    u.display_name
FROM dompet.locations l
LEFT JOIN dompet.vw_users_public u ON u.id = l.user_id
WHERE l.is_active = TRUE;

GRANT SELECT ON dompet.vw_locations TO web_user;
