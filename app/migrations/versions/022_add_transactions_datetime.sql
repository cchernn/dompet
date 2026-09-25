-- Adds hour:minute granularity alongside the existing date-only column.
-- `date` stays as-is (still required, still drives the existing
-- user_id/date index). All existing rows backfill to midnight of their
-- current date -- not an attempt to recover Firefly's originally-lost
-- timestamps (still recoverable separately via
-- transaction_operations.metadata->>'source_id' if ever wanted), just a
-- deliberate simple default per an explicit decision.

ALTER TABLE dompet.transactions ADD COLUMN datetime TIMESTAMPTZ;
UPDATE dompet.transactions SET datetime = date::timestamptz WHERE datetime IS NULL;
ALTER TABLE dompet.transactions ALTER COLUMN datetime SET NOT NULL;
