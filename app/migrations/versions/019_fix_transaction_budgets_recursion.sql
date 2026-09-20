-- Fixes a second, related recursion: transactions_select's policy checks
-- dompet.transaction_budgets (for shared-budget visibility), while
-- transaction_budgets' own policies check back into dompet.transactions
-- (for owned-transaction visibility) -- a circular dependency between two
-- different tables' RLS policies, which Postgres also reports as
-- "infinite recursion detected in policy" even though no single table
-- references itself. Same fix as 018: a SECURITY DEFINER function that
-- checks transaction ownership while bypassing RLS, so
-- transaction_budgets' policies no longer trigger transactions' own RLS
-- evaluation, breaking the cycle.

CREATE OR REPLACE FUNCTION dompet.owns_transaction(p_transaction_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1 FROM dompet.transactions
        WHERE id = p_transaction_id AND user_id = p_user_id
    );
$$;

REVOKE ALL ON FUNCTION dompet.owns_transaction(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.owns_transaction(uuid, uuid) TO web_user, web_role;

ALTER POLICY transaction_budgets_select ON dompet.transaction_budgets
    USING (
        dompet.owns_transaction(transaction_id, current_setting('app.current_user_id')::uuid)
        OR dompet.is_budget_member(budget_id, current_setting('app.current_user_id')::uuid)
    );

ALTER POLICY transaction_budgets_insert ON dompet.transaction_budgets
    WITH CHECK (
        dompet.owns_transaction(transaction_id, current_setting('app.current_user_id')::uuid)
        AND dompet.is_budget_member(budget_id, current_setting('app.current_user_id')::uuid)
    );

ALTER POLICY transaction_budgets_delete ON dompet.transaction_budgets
    USING (dompet.owns_transaction(transaction_id, current_setting('app.current_user_id')::uuid));
