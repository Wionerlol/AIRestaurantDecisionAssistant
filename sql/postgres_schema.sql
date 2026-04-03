CREATE TABLE restaurants (
    business_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(128) NOT NULL,
    state VARCHAR(16) NOT NULL,
    postal_code VARCHAR(16),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    stars DOUBLE PRECISION,
    review_count INTEGER NOT NULL DEFAULT 0,
    is_open INTEGER,
    categories JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE reviews (
    review_id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    business_id VARCHAR(32) NOT NULL REFERENCES restaurants (business_id) ON DELETE CASCADE,
    stars DOUBLE PRECISION NOT NULL,
    useful INTEGER NOT NULL DEFAULT 0,
    funny INTEGER NOT NULL DEFAULT 0,
    cool INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    review_date TIMESTAMP NOT NULL
);

CREATE INDEX idx_reviews_business_id ON reviews (business_id);
CREATE INDEX idx_reviews_review_date ON reviews (review_date);

CREATE TABLE restaurant_aspect_signals (
    business_id VARCHAR(32) PRIMARY KEY REFERENCES restaurants (business_id) ON DELETE CASCADE,
    overall_rating DOUBLE PRECISION,
    food_score DOUBLE PRECISION,
    service_score DOUBLE PRECISION,
    price_score DOUBLE PRECISION,
    ambience_score DOUBLE PRECISION,
    waiting_time_score DOUBLE PRECISION,
    pros JSONB NOT NULL DEFAULT '[]'::jsonb,
    cons JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
