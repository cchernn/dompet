ALTER TABLE dompet.locations
    DROP CONSTRAINT locations_check;

ALTER TABLE dompet.locations
    ADD CONSTRAINT locations_check
    CHECK (
        (type = 'online' AND url IS NOT NULL)
        OR
        (type = 'physical')
    );
