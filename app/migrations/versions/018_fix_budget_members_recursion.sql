-- Fixes "infinite recursion detected in policy for relation
-- budget_members" (and the knock-on recursion it caused in transactions/
-- transaction_budgets, since their policies join through budget_members).
-- budget_members_select's USING clause queried dompet.budget_members from
-- within its own policy -- RLS re-applies to that inner query too, so it
-- recurses forever. Standard fix: a SECURITY DEFINER function that checks
-- membership while bypassing RLS internally (owned by postgres, which
-- bypasses RLS, so the function's own internal query doesn't re-trigger
-- the policy), breaking the cycle.

CREATE OR REPLACE FUNCTION dompet.is_budget_member(p_budget_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = dompet, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1 FROM dompet.budget_members
        WHERE budget_id = p_budget_id AND user_id = p_user_id
    );
$$;

REVOKE ALL ON FUNCTION dompet.is_budget_member(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dompet.is_budget_member(uuid, uuid) TO web_user, web_role;

DROP POLICY budget_members_select ON dompet.budget_members;
CREATE POLICY budget_members_select ON dompet.budget_members
    FOR SELECT TO web_user, web_role
    USING (dompet.is_budget_member(budget_id, current_setting('app.current_user_id')::uuid));
