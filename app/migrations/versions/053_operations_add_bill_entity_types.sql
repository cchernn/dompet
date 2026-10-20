ALTER TABLE dompet.operations
    DROP CONSTRAINT operations_entity_type_check;

ALTER TABLE dompet.operations
    ADD CONSTRAINT operations_entity_type_check
    CHECK (entity_type IN (
        'transaction', 'account', 'category', 'location', 'tag', 'attachment', 'budget',
        'bill', 'bill_series'
    ));
