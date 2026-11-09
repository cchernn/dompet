-- vw_budgets gains: the owner's identity (owner_user_id + resolved
-- username/display_name via vw_users_public, same pattern as 049's
-- transaction/category/location search views), the member list as
-- usernames (ordered by when they joined; NULL entries are members who
-- haven't created a profile yet -- same nullability as budget_member's own
-- listing), and last_updated -- the most recent linked transaction's
-- datetime, not budgets.updated_at (that column reflects edits to the
-- budget's own name, not its transaction activity).
--
-- transaction_count and last_updated both count/scan every linked
-- transaction regardless of is_active, matching transaction_count's
-- existing behavior here (and vw_accounts' identical choice) -- not
-- reconsidering that now, just staying consistent with it.

CREATE OR REPLACE VIEW dompet.vw_budgets WITH (security_invoker = true) AS
SELECT
    b.id,
    b.name,
    (
        SELECT COUNT(*) FROM dompet.transaction_budgets tb WHERE tb.budget_id = b.id
    ) AS transaction_count,
    b.user_id AS owner_user_id,
    owner.username AS owner_username,
    owner.display_name AS owner_display_name,
    ARRAY(
        SELECT u.username
        FROM dompet.budget_members bm
        LEFT JOIN dompet.vw_users_public u ON u.id = bm.user_id
        WHERE bm.budget_id = b.id
        ORDER BY bm.created_at
    ) AS members,
    (
        SELECT MAX(t.datetime)
        FROM dompet.transaction_budgets tb
        JOIN dompet.transactions t ON t.id = tb.transaction_id
        WHERE tb.budget_id = b.id
    ) AS last_updated
FROM dompet.budgets b
LEFT JOIN dompet.vw_users_public owner ON owner.id = b.user_id
WHERE b.is_active = TRUE;

GRANT SELECT ON dompet.vw_budgets TO web_user;
