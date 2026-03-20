CREATE TABLE IF NOT EXISTS account (
    id         SERIAL PRIMARY KEY,
    login      VARCHAR(255) UNIQUE NOT NULL,
    password   VARCHAR(255) NOT NULL,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ads (
    id          SERIAL PRIMARY KEY,
    item_id     INTEGER UNIQUE NOT NULL,
    seller_id   INTEGER NOT NULL REFERENCES users(id),
    name        VARCHAR(500) NOT NULL,
    description TEXT DEFAULT '',
    category    INTEGER DEFAULT 0,
    images_qty  INTEGER DEFAULT 0,
    is_closed   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moderation_results (
    id            SERIAL PRIMARY KEY,
    item_id       INTEGER NOT NULL REFERENCES ads(id),
    status        VARCHAR(50) DEFAULT 'pending',
    is_violation  BOOLEAN,
    probability   DOUBLE PRECISION,
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    processed_at  TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ads_item_id ON ads(item_id);
CREATE INDEX IF NOT EXISTS idx_ads_seller_id ON ads(seller_id);
CREATE INDEX IF NOT EXISTS idx_moderation_item_id ON moderation_results(item_id);
CREATE INDEX IF NOT EXISTS idx_moderation_status ON moderation_results(status);

INSERT INTO account (login, password) VALUES ('admin', 'admin') ON CONFLICT DO NOTHING;
INSERT INTO users (username, is_verified) VALUES ('test_seller', TRUE) ON CONFLICT DO NOTHING;
