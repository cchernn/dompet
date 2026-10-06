-- Filter/search-dropdown views for accounts, categories, tags, budgets,
-- locations, attachments -- mirrors dompet.vw_transactions: security_invoker
-- = true so RLS evaluates against the querying role, not the view owner
-- (postgres, a superuser that bypasses RLS). Each base table's own SELECT
-- policy already encodes its correct visibility rule (owner-or-global for
-- categories, membership for budgets, ownership-via-parent for the
-- junction tables), so these views don't need to duplicate any of that --
-- and the usage_count subqueries' own target tables' RLS composes through
-- correctly too, scoping every count to what the calling user can see.
--
-- No stored usage_count column on the source tables (would need triggers/
-- app-level increment logic to stay correct) -- computed on read instead.

CREATE VIEW dompet.vw_accounts WITH (security_invoker = true) AS
SELECT
    a.id, a.code, a.name, a.description,
    (
        SELECT COUNT(*) FROM dompet.transactions t
        WHERE t.source_account_id = a.id OR t.destination_account_id = a.id
    ) AS usage_count
FROM dompet.accounts a
WHERE a.is_active = TRUE;

CREATE VIEW dompet.vw_categories WITH (security_invoker = true) AS
SELECT
    c.id, c.name, c.parent_id,
    (
        SELECT COUNT(*) FROM dompet.transactions t WHERE t.category_id = c.id
    ) AS usage_count
FROM dompet.categories c
WHERE c.is_active = TRUE;

CREATE VIEW dompet.vw_tags WITH (security_invoker = true) AS
SELECT
    tg.id, tg.name,
    (
        SELECT COUNT(*) FROM dompet.transaction_tags tt WHERE tt.tag_id = tg.id
    ) AS usage_count
FROM dompet.tags tg
WHERE tg.is_active = TRUE;

CREATE VIEW dompet.vw_budgets WITH (security_invoker = true) AS
SELECT
    b.id, b.name,
    (
        SELECT COUNT(*) FROM dompet.transaction_budgets tb WHERE tb.budget_id = b.id
    ) AS usage_count
FROM dompet.budgets b
WHERE b.is_active = TRUE;

CREATE VIEW dompet.vw_locations WITH (security_invoker = true) AS
SELECT
    l.id, l.name, l.type,
    (
        SELECT COUNT(*) FROM dompet.account_locations al WHERE al.location_id = l.id
    ) AS usage_count
FROM dompet.locations l
WHERE l.is_active = TRUE;

-- No usage_count (attachments aren't a "popular" filter dimension -- an
-- attachment is normally linked to exactly one transaction) and no
-- download_url (matches the existing list-endpoint decision to only
-- generate presigned URLs for a single GET /attachments/{id}, not eagerly
-- for every row in a list).
CREATE VIEW dompet.vw_attachments WITH (security_invoker = true) AS
SELECT id, filename, content_type, created_at
FROM dompet.attachments
WHERE is_active = TRUE;

GRANT SELECT ON dompet.vw_accounts TO web_user;
GRANT SELECT ON dompet.vw_categories TO web_user;
GRANT SELECT ON dompet.vw_tags TO web_user;
GRANT SELECT ON dompet.vw_budgets TO web_user;
GRANT SELECT ON dompet.vw_locations TO web_user;
GRANT SELECT ON dompet.vw_attachments TO web_user;
