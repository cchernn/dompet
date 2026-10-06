ALTER TABLE dompet.locations ADD COLUMN user_id UUID;

-- Existing rows stay NULL (public) -- no visibility change for current data.

DROP POLICY locations_all ON dompet.locations;

CREATE POLICY locations_select ON dompet.locations
    FOR SELECT TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid OR user_id IS NULL);

-- Also allows user_id IS NULL so a caller can explicitly create a public
-- location (app/db/location.py gates this behind an explicit `is_public`
-- request flag -- there's no approval step, any user can self-mark a
-- location public).
CREATE POLICY locations_insert ON dompet.locations
    FOR INSERT TO web_user
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid OR user_id IS NULL);

-- No "OR user_id IS NULL" here -- a public location can never be updated
-- or deleted through the app once created (matches dompet.categories'
-- existing global-row behavior exactly).
CREATE POLICY locations_update ON dompet.locations
    FOR UPDATE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY locations_delete ON dompet.locations
    FOR DELETE TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid);
