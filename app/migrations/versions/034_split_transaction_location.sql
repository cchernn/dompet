-- vw_transactions references location_id and must be dropped before that
-- column can be dropped below; 035 recreates it against the new columns.
DROP VIEW IF EXISTS dompet.vw_transactions;

ALTER TABLE dompet.transactions ADD COLUMN source_location_id UUID REFERENCES dompet.locations (id);
ALTER TABLE dompet.transactions ADD COLUMN destination_location_id UUID REFERENCES dompet.locations (id);

-- Backfill from the single location_id column being replaced: a location
-- only ever validated as belonging to the source account, the destination
-- account, or (rarely) both -- assign it to whichever leg(s) it's actually
-- linked to via account_locations.
UPDATE dompet.transactions t
SET source_location_id = t.location_id
WHERE t.location_id IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM dompet.account_locations al
      WHERE al.account_id = t.source_account_id AND al.location_id = t.location_id
  );

UPDATE dompet.transactions t
SET destination_location_id = t.location_id
WHERE t.location_id IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM dompet.account_locations al
      WHERE al.account_id = t.destination_account_id AND al.location_id = t.location_id
  );

DROP INDEX IF EXISTS dompet.idx_transactions_location_id;
ALTER TABLE dompet.transactions DROP COLUMN location_id;

CREATE INDEX idx_transactions_source_location_id
    ON dompet.transactions (source_location_id)
    WHERE source_location_id IS NOT NULL;

CREATE INDEX idx_transactions_destination_location_id
    ON dompet.transactions (destination_location_id)
    WHERE destination_location_id IS NOT NULL;
