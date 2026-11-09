-- Profile picture storage. One avatar per user at a fixed S3 key
-- (profiles/{user_id}/avatar) -- a replacement upload overwrites the same
-- object, so unlike dompet.attachments (a collection, unique key per file,
-- explicit S3 delete on row delete) there's never an orphaned old file to
-- clean up. No grant changes needed: the existing table-level
-- SELECT/INSERT/UPDATE grants on dompet.users already cover this column.

ALTER TABLE dompet.users ADD COLUMN avatar_storage_key TEXT;
