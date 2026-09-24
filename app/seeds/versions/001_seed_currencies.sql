INSERT INTO dompet.currencies (code, name, symbol, decimal_places) VALUES
    ('MYR', 'Malaysian Ringgit', 'RM', 2),
    ('USD', 'US Dollar', '$', 2),
    ('SGD', 'Singapore Dollar', 'S$', 2),
    ('EUR', 'Euro', '€', 2),
    ('GBP', 'British Pound', '£', 2)
ON CONFLICT (code) DO NOTHING;
