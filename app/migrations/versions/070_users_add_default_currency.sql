-- A user's preferred currency, so the web app can lead with it when a
-- summary spans several currencies. Nullable: users who haven't chosen
-- one get currencies ordered by activity instead. Not exposed through
-- vw_users_public -- like the rest of the profile settings it is owner-only.
ALTER TABLE dompet.users
    ADD COLUMN default_currency CHAR(3) REFERENCES dompet.currencies (code);
