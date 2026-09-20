-- Grants dompet.* access to "web_role", a second test role created
-- specifically to debug the web_user EAUTHQUERY/pooler-secret issue in
-- isolation, without touching web_user (which still works correctly for
-- public.* and is left completely alone here). Extends each existing
-- policy's role list to cover both roles via ALTER POLICY, rather than
-- creating duplicate policy objects with identical logic.

GRANT USAGE ON SCHEMA dompet TO web_role;

GRANT SELECT ON dompet.currencies TO web_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.locations TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.accounts TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.tags TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.attachments TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_operations TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.categories TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.account_locations TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_tags TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transaction_attachments TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.transactions TO web_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.budgets TO web_role;
GRANT SELECT, INSERT, DELETE ON dompet.budget_members TO web_role;
GRANT SELECT, INSERT, DELETE ON dompet.transaction_budgets TO web_role;

ALTER POLICY locations_all ON dompet.locations TO web_user, web_role;
ALTER POLICY accounts_all ON dompet.accounts TO web_user, web_role;
ALTER POLICY tags_all ON dompet.tags TO web_user, web_role;
ALTER POLICY attachments_all ON dompet.attachments TO web_user, web_role;
ALTER POLICY transaction_operations_all ON dompet.transaction_operations TO web_user, web_role;

ALTER POLICY categories_select ON dompet.categories TO web_user, web_role;
ALTER POLICY categories_insert ON dompet.categories TO web_user, web_role;
ALTER POLICY categories_update ON dompet.categories TO web_user, web_role;
ALTER POLICY categories_delete ON dompet.categories TO web_user, web_role;

ALTER POLICY account_locations_all ON dompet.account_locations TO web_user, web_role;
ALTER POLICY transaction_tags_all ON dompet.transaction_tags TO web_user, web_role;
ALTER POLICY transaction_attachments_all ON dompet.transaction_attachments TO web_user, web_role;

ALTER POLICY transactions_select ON dompet.transactions TO web_user, web_role;
ALTER POLICY transactions_insert ON dompet.transactions TO web_user, web_role;
ALTER POLICY transactions_update ON dompet.transactions TO web_user, web_role;
ALTER POLICY transactions_delete ON dompet.transactions TO web_user, web_role;

ALTER POLICY budgets_select ON dompet.budgets TO web_user, web_role;
ALTER POLICY budgets_insert ON dompet.budgets TO web_user, web_role;
ALTER POLICY budgets_update ON dompet.budgets TO web_user, web_role;
ALTER POLICY budgets_delete ON dompet.budgets TO web_user, web_role;

ALTER POLICY budget_members_select ON dompet.budget_members TO web_user, web_role;
ALTER POLICY budget_members_insert ON dompet.budget_members TO web_user, web_role;
ALTER POLICY budget_members_delete ON dompet.budget_members TO web_user, web_role;

ALTER POLICY transaction_budgets_select ON dompet.transaction_budgets TO web_user, web_role;
ALTER POLICY transaction_budgets_insert ON dompet.transaction_budgets TO web_user, web_role;
ALTER POLICY transaction_budgets_delete ON dompet.transaction_budgets TO web_user, web_role;
