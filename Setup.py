from Database import Database

def main(params, db):
    createTransactionTable(db)

def createTransactionTable(db):
    db.create("transactions", [
        ("user", "UUID NOT NULL"),
        ("date", "DATE NOT NULL"),
        ("name", "VARCHAR(255)"),
        ("location", "VARCHAR(255)"),
        ("type", "VARCHAR(255) DEFAULT 'expenditure'"),
        ("amount", "DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (amount >= 0)"),
        ("currency", "VARCHAR(3) DEFAULT 'MYR'"),
        ("payment_method", "VARCHAR(255)"),
        ("category", "VARCHAR(255) DEFAULT 'others'"),
        ("attachment", "VARCHAR(255)"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ])

