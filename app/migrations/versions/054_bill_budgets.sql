-- Bills gain the same budget-tying/sharing mechanism transactions already
-- have: dompet.bill_budgets is a direct mirror of dompet.transaction_budgets,
-- and dompet.bills/dompet.bill_payments get the same "owner OR budget
-- member" SELECT split dompet.transactions already has (see
-- 016_web_user_rls.sql's transactions_select) -- the single FOR ALL
-- bills_all/bill_payments_all policies can't express that (different
-- USING clause per command), so they're replaced with the same 4-policy
-- split transactions uses.
--
-- bill_attachments is deliberately left untouched (strict owner-only, no
-- budget clause) -- matches transaction_attachments' own documented choice
-- (owned via parent, no budget-sharing); a budget co-member seeing a
-- shared bill won't see its attachments, same existing limitation
-- transactions have at that layer.
--
-- Payment writes (insert/update/delete) stay owner-only -- only visibility
-- was asked for, not letting another budget member record a payment
-- against someone else's bill.

CREATE TABLE IF NOT EXISTS dompet.bill_budgets (
    bill_id UUID NOT NULL
        REFERENCES dompet.bills (id),
    budget_id UUID NOT NULL
        REFERENCES dompet.budgets (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (bill_id, budget_id)
);

GRANT SELECT, INSERT, DELETE ON dompet.bill_budgets TO web_user;
ALTER TABLE dompet.bill_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.bill_budgets FORCE ROW LEVEL SECURITY;

CREATE POLICY bill_budgets_select ON dompet.bill_budgets
    FOR SELECT TO web_user
    USING (
        EXISTS (
            SELECT 1 FROM dompet.bills b
            WHERE b.id = bill_budgets.bill_id
              AND b.user_id = current_setting('app.current_user_id')::uuid
        )
        OR EXISTS (
            SELECT 1 FROM dompet.budget_members bm
            WHERE bm.budget_id = bill_budgets.budget_id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY bill_budgets_insert ON dompet.bill_budgets
    FOR INSERT TO web_user
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM dompet.bills b
            WHERE b.id = bill_budgets.bill_id
              AND b.user_id = current_setting('app.current_user_id')::uuid
        )
        AND EXISTS (
            SELECT 1 FROM dompet.budget_members bm
            WHERE bm.budget_id = bill_budgets.budget_id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY bill_budgets_delete ON dompet.bill_budgets
    FOR DELETE TO web_user
    USING (EXISTS (
        SELECT 1 FROM dompet.bills b
        WHERE b.id = bill_budgets.bill_id
          AND b.user_id = current_setting('app.current_user_id')::uuid
    ));

DROP POLICY IF EXISTS bills_all ON dompet.bills;

CREATE POLICY bills_select ON dompet.bills
    FOR SELECT TO web_user
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR EXISTS (
            SELECT 1 FROM dompet.bill_budgets bb
            JOIN dompet.budget_members bm ON bm.budget_id = bb.budget_id
            WHERE bb.bill_id = bills.id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY bills_insert ON dompet.bills
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY bills_update ON dompet.bills
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY bills_delete ON dompet.bills
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

DROP POLICY IF EXISTS bill_payments_all ON dompet.bill_payments;

CREATE POLICY bill_payments_select ON dompet.bill_payments
    FOR SELECT TO web_user
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR EXISTS (
            SELECT 1 FROM dompet.bill_budgets bb
            JOIN dompet.budget_members bm ON bm.budget_id = bb.budget_id
            WHERE bb.bill_id = bill_payments.bill_id
              AND bm.user_id = current_setting('app.current_user_id')::uuid
        )
    );
CREATE POLICY bill_payments_insert ON dompet.bill_payments
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY bill_payments_update ON dompet.bill_payments
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY bill_payments_delete ON dompet.bill_payments
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- vw_bills (and its paid_amount/status LATERAL subquery) needs no SQL
-- changes at all -- security_invoker = true means it automatically picks
-- up the widened bills/bill_payments SELECT policies above. category/
-- account names will show NULL for a co-member viewing a shared bill
-- (dompet.categories/dompet.accounts stay strictly owner-only, same
-- limitation dompet.vw_transactions has for a budget co-member without
-- going through shared_transaction_details()).
