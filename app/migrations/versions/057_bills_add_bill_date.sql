-- Bills gain a bill_date (the date the bill was issued/statemented),
-- distinct from due_date (when payment is due). For a recurring series,
-- generation now advances by bill_date, not due_date: anchor_date is the
-- first bill_date, and each occurrence's due_date defaults to the day
-- before the *next* occurrence's bill_date (see
-- app/db/bill.py's _generate_due_occurrences) -- e.g. a credit card
-- statement issued on the 15th of each month is due the day before the
-- next statement, the 14th of the following month.
--
-- Backfill: every existing bill's bill_date is set equal to its current
-- due_date (the two were the same concept before this column existed, so
-- this changes no observed behavior for bills already created -- only
-- bills created from now on can have bill_date != due_date).

ALTER TABLE dompet.bills ADD COLUMN IF NOT EXISTS bill_date DATE;

UPDATE dompet.bills SET bill_date = due_date WHERE bill_date IS NULL;

ALTER TABLE dompet.bills ALTER COLUMN bill_date SET NOT NULL;

-- The generator dedupes against bill_date now (the field it actually
-- advances by), not due_date.
DROP INDEX IF EXISTS dompet.bills_series_due_date_unique;

CREATE UNIQUE INDEX IF NOT EXISTS bills_series_bill_date_unique
    ON dompet.bills (series_id, bill_date)
    WHERE series_id IS NOT NULL;

-- Appended at the end, not alongside due_date, so this stays a safe
-- CREATE OR REPLACE (same convention as 049_search_results_add_username.sql).
CREATE OR REPLACE VIEW dompet.vw_bills WITH (security_invoker = true) AS
SELECT
    b.id,
    b.name,
    b.due_date,
    b.amount,
    b.currency_code AS currency,
    c.name AS category,
    a.name AS account,
    (b.series_id IS NOT NULL) AS is_recurring,
    COALESCE(p.paid_amount, 0.00) AS paid_amount,
    CASE
        WHEN COALESCE(p.paid_amount, 0.00) >= b.amount THEN 'paid'
        WHEN COALESCE(p.paid_amount, 0.00) > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS status,
    (b.due_date < CURRENT_DATE AND COALESCE(p.paid_amount, 0.00) < b.amount) AS is_overdue,
    (
        SELECT COUNT(*) FROM dompet.bill_attachments ba WHERE ba.bill_id = b.id
    ) AS attachment_count,
    b.bill_date
FROM dompet.bills b
LEFT JOIN dompet.categories c ON c.id = b.category_id
LEFT JOIN dompet.accounts a ON a.id = b.account_id
LEFT JOIN LATERAL (
    SELECT SUM(bp.amount_paid) AS paid_amount
    FROM dompet.bill_payments bp
    WHERE bp.bill_id = b.id
) p ON TRUE
WHERE b.is_active = TRUE;

GRANT SELECT ON dompet.vw_bills TO web_user;
