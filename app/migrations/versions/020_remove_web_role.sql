-- Reverts everything migration 017 (and the web_role grants added
-- alongside 018/019's function fixes) did for "web_role" -- the temporary
-- role created to debug the web_user EAUTHQUERY/pooler-secret issue in
-- isolation. That issue is resolved (web_user's password was reset), so
-- web_role is no longer needed. Every dompet.* policy goes back to
-- targeting web_user only, matching migration 016's original state.

ALTER POLICY locations_all ON dompet.locations TO web_user;
ALTER POLICY accounts_all ON dompet.accounts TO web_user;
ALTER POLICY tags_all ON dompet.tags TO web_user;
ALTER POLICY attachments_all ON dompet.attachments TO web_user;
ALTER POLICY transaction_operations_all ON dompet.transaction_operations TO web_user;

ALTER POLICY categories_select ON dompet.categories TO web_user;
ALTER POLICY categories_insert ON dompet.categories TO web_user;
ALTER POLICY categories_update ON dompet.categories TO web_user;
ALTER POLICY categories_delete ON dompet.categories TO web_user;

ALTER POLICY account_locations_all ON dompet.account_locations TO web_user;
ALTER POLICY transaction_tags_all ON dompet.transaction_tags TO web_user;
ALTER POLICY transaction_attachments_all ON dompet.transaction_attachments TO web_user;

ALTER POLICY transactions_select ON dompet.transactions TO web_user;
ALTER POLICY transactions_insert ON dompet.transactions TO web_user;
ALTER POLICY transactions_update ON dompet.transactions TO web_user;
ALTER POLICY transactions_delete ON dompet.transactions TO web_user;

ALTER POLICY budgets_select ON dompet.budgets TO web_user;
ALTER POLICY budgets_insert ON dompet.budgets TO web_user;
ALTER POLICY budgets_update ON dompet.budgets TO web_user;
ALTER POLICY budgets_delete ON dompet.budgets TO web_user;

ALTER POLICY budget_members_select ON dompet.budget_members TO web_user;
ALTER POLICY budget_members_insert ON dompet.budget_members TO web_user;
ALTER POLICY budget_members_delete ON dompet.budget_members TO web_user;

ALTER POLICY transaction_budgets_select ON dompet.transaction_budgets TO web_user;
ALTER POLICY transaction_budgets_insert ON dompet.transaction_budgets TO web_user;
ALTER POLICY transaction_budgets_delete ON dompet.transaction_budgets TO web_user;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA dompet FROM web_role;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA dompet FROM web_role;
REVOKE USAGE ON SCHEMA dompet FROM web_role;

DROP ROLE web_role;
