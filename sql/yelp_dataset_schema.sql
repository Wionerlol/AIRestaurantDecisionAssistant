-- Yelp dataset relational schema inferred from the JSON Lines files in yelp_dataset/.
-- Main table per source file, plus child tables for repeated or nested fields.

CREATE TABLE businesses (
    business_id VARCHAR(32) PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    city VARCHAR(128),
    state VARCHAR(16),
    postal_code VARCHAR(16),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    stars DECIMAL(2, 1),
    review_count INTEGER,
    is_open SMALLINT,
    categories_text TEXT
);

CREATE TABLE business_categories (
    business_id VARCHAR(32) NOT NULL,
    category_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (business_id, category_name),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE business_attributes (
    business_id VARCHAR(32) NOT NULL,
    attribute_name VARCHAR(255) NOT NULL,
    attribute_value TEXT,
    PRIMARY KEY (business_id, attribute_name),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE business_hours (
    business_id VARCHAR(32) NOT NULL,
    day_of_week VARCHAR(16) NOT NULL,
    open_close_range VARCHAR(64) NOT NULL,
    PRIMARY KEY (business_id, day_of_week),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE users (
    user_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    review_count INTEGER,
    yelping_since TIMESTAMP,
    useful INTEGER,
    funny INTEGER,
    cool INTEGER,
    fans INTEGER,
    average_stars DECIMAL(3, 2),
    elite_text TEXT,
    friends_text TEXT,
    compliment_hot INTEGER,
    compliment_more INTEGER,
    compliment_profile INTEGER,
    compliment_cute INTEGER,
    compliment_list INTEGER,
    compliment_note INTEGER,
    compliment_plain INTEGER,
    compliment_cool INTEGER,
    compliment_funny INTEGER,
    compliment_writer INTEGER,
    compliment_photos INTEGER
);

CREATE TABLE user_elite_years (
    user_id VARCHAR(32) NOT NULL,
    elite_year SMALLINT NOT NULL,
    PRIMARY KEY (user_id, elite_year),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE user_friends (
    user_id VARCHAR(32) NOT NULL,
    friend_user_id VARCHAR(32) NOT NULL,
    PRIMARY KEY (user_id, friend_user_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE reviews (
    review_id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    business_id VARCHAR(32) NOT NULL,
    stars DECIMAL(2, 1) NOT NULL,
    useful INTEGER,
    funny INTEGER,
    cool INTEGER,
    text TEXT NOT NULL,
    review_date TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE tips (
    user_id VARCHAR(32) NOT NULL,
    business_id VARCHAR(32) NOT NULL,
    tip_date TIMESTAMP NOT NULL,
    text TEXT NOT NULL,
    compliment_count INTEGER,
    PRIMARY KEY (user_id, business_id, tip_date),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE checkins (
    business_id VARCHAR(32) PRIMARY KEY,
    date_text TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE TABLE checkin_events (
    business_id VARCHAR(32) NOT NULL,
    checkin_time TIMESTAMP NOT NULL,
    PRIMARY KEY (business_id, checkin_time),
    FOREIGN KEY (business_id) REFERENCES businesses (business_id)
);

CREATE INDEX idx_businesses_city_state ON businesses (city, state);
CREATE INDEX idx_reviews_user_id ON reviews (user_id);
CREATE INDEX idx_reviews_business_id ON reviews (business_id);
CREATE INDEX idx_reviews_review_date ON reviews (review_date);
CREATE INDEX idx_tips_business_id ON tips (business_id);
CREATE INDEX idx_checkin_events_business_id ON checkin_events (business_id);
