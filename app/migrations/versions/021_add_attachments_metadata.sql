-- Adds a metadata column to dompet.attachments, mirroring
-- dompet.transaction_operations.metadata's {"source": ..., "source_id": ...}
-- convention. Regular API-created attachments (POST /attachments) leave
-- this NULL; migration scripts use it to tag provenance and to detect
-- already-migrated rows on re-run, since attachments have no other natural
-- dedup key (unlike budgets/tags/categories, which dedupe by unique name).

ALTER TABLE dompet.attachments ADD COLUMN IF NOT EXISTS metadata JSONB;
