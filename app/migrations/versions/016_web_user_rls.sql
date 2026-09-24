-- Row-level security for dompet.* under the restricted "web_user" role,
-- mirroring the proven pattern already in place on public.* (grants + RLS
-- + policies keyed on current_setting('app.current_user_id')::uuid, set
-- per-connection by app/utils/db.py::connect()). Has no effect on
-- "postgres" (admin/BYPASSRLS), which is what local dev and every
-- migration script uses.

GRANT USAGE ON SCHEMA dompet TO web_user;

-- Global reference data: read-only, no RLS (matches how public.*'s
-- lookup-style tables, e.g. auth_group, never got RLS either). SELECT is
-- needed for the FK check when a transaction references currency_code.
GRANT SELECT ON dompet.currencies TO web_user;

-- Fully open, no ownership concept (matches public.locations exactly).
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.locations TO web_user;
ALTER TABLE dompet.locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.locations FORCE ROW LEVEL SECURITY;
CREATE POLICY locations_all ON dompet.locations
    FOR ALL TO web_user
    USING (true)
    WITH CHECK (true);

-- Directly owned, simple user_id match.
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.accounts TO web_user;
ALTER TABLE dompet.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY accounts_all ON dompet.accounts
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.tags TO web_user;
ALTER TABLE dompet.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.tags FORCE ROW LEVEL SECURITY;
CREATE POLICY tags_all ON dompet.tags
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.attachments TO web_user;
ALTER TABLE dompet.attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY attachments_all ON dompet.attachments
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_operations TO web_user;
ALTER TABLE dompet.transaction_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.transaction_operations FORCE ROW LEVEL SECURITY;
CREATE POLICY transaction_operations_all ON dompet.transaction_operations
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

-- Owned, but user_id is nullable (NULL = global category). SELECT sees
-- both; writes only ever touch the caller's own rows (matches
-- create_category/update_category/delete_category's app logic exactly).
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.categories TO web_user;
ALTER TABLE dompet.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.categories FORCE ROW LEVEL SECURITY;
CREATE POLICY categories_select ON dompet.categories
    FOR SELECT TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid OR user_id IS NULL);
CREATE POLICY categories_insert ON dompet.categories
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY categories_update ON dompet.categories
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY categories_delete ON dompet.categories
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Owned via the parent account (matches account_location.py's own
-- _require_owned_account check -- strict ownership, no sharing).
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.account_locations TO web_user;
ALTER TABLE dompet.account_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.account_locations FORCE ROW LEVEL SECURITY;
CREATE POLICY account_locations_all ON dompet.account_locations
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.accounts a
        WHERE a.id = account_locations.account_id
          AND a.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.accounts a
        WHERE a.id = account_locations.account_id
          AND a.user_id = current_setting('app.current_user_id')::uuid
    ));

-- Owned via the parent transaction (matches transaction_tag.py's/
-- transaction_attachment.py's own _require_owned_transaction check --
-- strict ownership, no budget-sharing).
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_tags TO web_user;
ALTER TABLE dompet.transaction_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.transaction_tags FORCE ROW LEVEL SECURITY;
CREATE POLICY transaction_tags_all ON dompet.transaction_tags
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.transactions t
        WHERE t.id = transaction_tags.transaction_id
          AND t.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.transactions t
        WHERE t.id = transaction_tags.transaction_id
          AND t.user_id = current_setting('app.current_user_id')::uuid
    ));

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_attachments TO web_user;
ALTER TABLE dompet.transaction_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.transaction_attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY transaction_attachments_all ON dompet.transaction_attachments
    FOR ALL TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.transactions t
        WHERE t.id = transaction_attachments.transaction_id
          AND t.user_id = current_setting('app.current_user_id')::uuid
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.transactions t
        WHERE t.id = transaction_attachments.transaction_id
          AND t.user_id = current_setting('app.current_user_id')::uuid
    ));

-- Transactions: owner always has full access; SELECT is also extended to
-- anyone sharing a budget the transaction is linked to (mirrors
-- public.transactions_get's OR-based sharing clause, swapping
-- transaction_groups/user_transaction_group for
-- transaction_budgets/budget_members). Without this,
-- GET /budgets/{id}/transactions would silently come back empty for
-- every row but the caller's own once RLS is on.
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transactions TO web_user;
ALTER TABLE dompet.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.transactions FORCE ROW LEVEL SECURITY;
CREATE POLICY transactions_select ON dompet.transactions
    FOR SELECT TO web_user
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR EXISTS (
            SELECT 1 FROM dompet.transaction_budgets tb
            JOIN dompet.budget_members bm ON bm.budget_id = tb.budget_id
            WHERE tb.transaction_id = transactions.id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY transactions_insert ON dompet.transactions
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY transactions_update ON dompet.transactions
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY transactions_delete ON dompet.transactions
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Budgets: visibility is membership-based, not ownership-based (matches
-- list_budgets/get_budget's own JOIN budget_members). Only the owner can
-- edit/delete (matches update_budget/delete_budget).
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.budgets TO web_user;
ALTER TABLE dompet.budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.budgets FORCE ROW LEVEL SECURITY;
CREATE POLICY budgets_select ON dompet.budgets
    FOR SELECT TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.budget_members bm
        WHERE bm.budget_id = budgets.id
          AND bm.user_id = current_setting('app.current_user_id')::uuid
    ));
CREATE POLICY budgets_insert ON dompet.budgets
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY budgets_update ON dompet.budgets
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY budgets_delete ON dompet.budgets
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Budget members: new pattern, no v1 equivalent (old user_transaction_group
-- never supported "list all members"). Any member can see the full member
-- list (matches list_members' own membership check, a standard
-- self-referencing EXISTS); only the owner can add/remove members
-- (matches budget_member.py's _require_owner).
GRANT SELECT, INSERT, DELETE ON dompet.budget_members TO web_user;
ALTER TABLE dompet.budget_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.budget_members FORCE ROW LEVEL SECURITY;
CREATE POLICY budget_members_select ON dompet.budget_members
    FOR SELECT TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.budget_members bm2
        WHERE bm2.budget_id = budget_members.budget_id
          AND bm2.user_id = current_setting('app.current_user_id')::uuid
    ));
CREATE POLICY budget_members_insert ON dompet.budget_members
    FOR INSERT TO web_user
    WITH CHECK (EXISTS (
        SELECT 1 FROM dompet.budgets b
        WHERE b.id = budget_members.budget_id
          AND b.user_id = current_setting('app.current_user_id')::uuid
    ));
CREATE POLICY budget_members_delete ON dompet.budget_members
    FOR DELETE TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.budgets b
        WHERE b.id = budget_members.budget_id
          AND b.user_id = current_setting('app.current_user_id')::uuid
    ));

-- Transaction <-> budget links: matches link_budget (owned transaction AND
-- budget membership required), unlink_budget (owned transaction only),
-- and both list_transaction_budgets/list_budget_transactions (either an
-- owned transaction or budget membership is enough to see a link).
GRANT SELECT, INSERT, DELETE ON dompet.transaction_budgets TO web_user;
ALTER TABLE dompet.transaction_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.transaction_budgets FORCE ROW LEVEL SECURITY;
CREATE POLICY transaction_budgets_select ON dompet.transaction_budgets
    FOR SELECT TO web_user
    USING (
        EXISTS (
            SELECT 1 FROM dompet.transactions t
            WHERE t.id = transaction_budgets.transaction_id
              AND t.user_id = current_setting('app.current_user_id')::uuid
        )
        OR EXISTS (
            SELECT 1 FROM dompet.budget_members bm
            WHERE bm.budget_id = transaction_budgets.budget_id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY transaction_budgets_insert ON dompet.transaction_budgets
    FOR INSERT TO web_user
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM dompet.transactions t
            WHERE t.id = transaction_budgets.transaction_id
              AND t.user_id = current_setting('app.current_user_id')::uuid
        )
        AND EXISTS (
            SELECT 1 FROM dompet.budget_members bm
            WHERE bm.budget_id = transaction_budgets.budget_id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY transaction_budgets_delete ON dompet.transaction_budgets
    FOR DELETE TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.transactions t
        WHERE t.id = transaction_budgets.transaction_id
          AND t.user_id = current_setting('app.current_user_id')::uuid
    ));

-- schema_migrations / seed_versions are intentionally untouched -- web_user
-- never accesses them at runtime, only admin/migration scripts do.
