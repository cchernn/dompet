-- User profile module. id is the same Cognito sub already used everywhere
-- else as user_id (no separate surrogate key, no FK -- matches how every
-- other dompet.* table just stores the raw Cognito UUID). username is the
-- new public identifier: other people (e.g. a budget owner inviting a
-- member) address a user by username instead of needing their Cognito UUID.

CREATE TABLE dompet.users (
    id UUID PRIMARY KEY,
    username VARCHAR(30) NOT NULL,
    display_name VARCHAR(100),
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive uniqueness ("Alice" and "alice" are the same handle).
CREATE UNIQUE INDEX idx_users_username_lower ON dompet.users (LOWER(username));

GRANT SELECT, INSERT, UPDATE ON dompet.users TO web_user;
ALTER TABLE dompet.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.users FORCE ROW LEVEL SECURITY;

-- Full-row access (including configuration) is owner-only. Other users'
-- public columns are reached through vw_users_public below, never through
-- this table directly.
CREATE POLICY users_select ON dompet.users
    FOR SELECT TO web_user
    USING (id = current_setting('app.current_user_id')::uuid);
CREATE POLICY users_insert ON dompet.users
    FOR INSERT TO web_user
    WITH CHECK (id = current_setting('app.current_user_id')::uuid);
CREATE POLICY users_update ON dompet.users
    FOR UPDATE TO web_user
    USING (id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (id = current_setting('app.current_user_id')::uuid);

-- Public directory view, used to resolve a username to an id (e.g. inviting
-- a budget member by username) and to show another member's username
-- instead of their raw Cognito UUID. Deliberately NOT security_invoker --
-- every other vw_* view uses security_invoker so RLS filters rows down to
-- what the caller owns/can see; this one needs the opposite, so it stays a
-- definer-rights view (runs as its owner, the migration role, which
-- bypasses RLS like every other admin/migration script) and limits exposure
-- itself by only selecting non-sensitive columns -- configuration and
-- updated_at are never exposed here.
CREATE VIEW dompet.vw_users_public AS
SELECT id, username, display_name, created_at
FROM dompet.users;

GRANT SELECT ON dompet.vw_users_public TO web_user;
