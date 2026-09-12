INSERT INTO dompet.categories (name) VALUES
    ('Others'),
    ('Food'),
    ('Transport'),
    ('Shopping'),
    ('Bills'),
    ('Entertainment'),
    ('Salary'),
    ('Freelance'),
    ('Investment'),
    ('Transfer')
ON CONFLICT (parent_id, name) WHERE user_id IS NULL DO NOTHING;
