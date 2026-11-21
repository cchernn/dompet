-- /transactions/search shows source/destination location names; also
-- surface each location's links so the UI can open the map or site
-- directly. google_maps_url is the physical-location link, url the
-- online-location one; either may be NULL.
--
-- Appended at the end of the column list (CREATE OR REPLACE VIEW can only
-- add columns there); every existing column is unchanged. A location the
-- viewer can't read (another user's, seen only through a shared budget)
-- has no joinable row, so its URLs are NULL -- the same case where the
-- name already falls back to shared_transaction_details.

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
                SELECT json_build_object('id', att.id, 'filename', att.filename) AS x
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
    u.display_name,
    src_loc.google_maps_url AS source_location_google_maps_url,
    src_loc.url AS source_location_url,
    dst_loc.google_maps_url AS destination_location_google_maps_url,
    dst_loc.url AS destination_location_url
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
