-- bills_select checked bill_budgets, and bill_budgets_select checked bills
-- -- each policy's evaluation requires evaluating the other's, forever.
-- Postgres detects this and raises "infinite recursion detected in policy
-- for relation ...". Hit in production via /transactions/search (vw_transactions
-- looks up bill names, which touches dompet.bills under RLS) and /bills/search
-- (sync_bills touches dompet.bills directly).
--
-- Fix: route the "is this bill shared with me via a budget" check through a
-- SECURITY DEFINER function, same pattern as shared_transaction_details().
-- Its internal query against bill_budgets runs as the function owner,
-- bypassing bill_budgets' own RLS entirely -- so evaluating bills_select
-- never re-enters bill_budgets_select, and the cycle is broken.

CREATE OR REPLACE FUNCTION dompet.bill_shared_via_budget(target_bill_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM dompet.bill_budgets bb
        JOIN dompet.budget_members bm ON bm.budget_id = bb.budget_id
        WHERE bb.bill_id = target_bill_id
          AND bm.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );
$$;

REVOKE ALL ON FUNCTION dompet.bill_shared_via_budget(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.bill_shared_via_budget(uuid) TO web_user;

DROP POLICY IF EXISTS bills_select ON dompet.bills;
CREATE POLICY bills_select ON dompet.bills
    FOR SELECT TO web_user
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR dompet.bill_shared_via_budget(id)
    );

DROP POLICY IF EXISTS bill_payments_select ON dompet.bill_payments;
CREATE POLICY bill_payments_select ON dompet.bill_payments
    FOR SELECT TO web_user
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR dompet.bill_shared_via_budget(bill_id)
    );
