-- Physical locations must have a country (set by 063's backfill for all
-- existing rows). Online locations have none.
ALTER TABLE dompet.locations
    ADD CONSTRAINT locations_physical_country_check CHECK (type <> 'physical' OR country IS NOT NULL);
