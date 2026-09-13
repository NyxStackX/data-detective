CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR(50) PRIMARY KEY,
    entity_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    parent_entity_id VARCHAR(50),
    country VARCHAR(100),
    city VARCHAR(100),
    industry VARCHAR(150),
    creation_date DATE,
    status VARCHAR(50),
    CONSTRAINT fk_entity_parent
        FOREIGN KEY (parent_entity_id)
        REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    entity_id VARCHAR(50) NOT NULL,
    bank_name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    city VARCHAR(100),
    currency VARCHAR(10) NOT NULL,
    account_type VARCHAR(100),
    opening_date DATE,
    closing_date DATE,
    status VARCHAR(50),
    CONSTRAINT fk_account_entity
        FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    transaction_date TIMESTAMP NOT NULL,
    source_account_id VARCHAR(50) NOT NULL,
    destination_account_id VARCHAR(50) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    transaction_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    authorized_by VARCHAR(50),
    created_by VARCHAR(50),
    CONSTRAINT fk_transaction_source
        FOREIGN KEY (source_account_id)
        REFERENCES accounts(account_id),
    CONSTRAINT fk_transaction_destination
        FOREIGN KEY (destination_account_id)
        REFERENCES accounts(account_id),
    CONSTRAINT chk_transaction_amount
        CHECK (amount > 0)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_source
    ON transactions(source_account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_destination
    ON transactions(destination_account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_type
    ON transactions(transaction_type);

CREATE INDEX IF NOT EXISTS idx_accounts_entity
    ON accounts(entity_id);
