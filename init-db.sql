-- ============================================================
-- LUMINALIB DATABASE INITIALIZATION SCRIPT (UPDATED)
-- ============================================================


-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);


-- ============================================================
-- USER PROFILES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,

    user_id INTEGER UNIQUE NOT NULL,

    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    avatar_url TEXT,
    bio TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);


CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,

    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    refresh_token_hash TEXT NOT NULL UNIQUE,

    user_agent TEXT,
    ip_address TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);


-- ============================================================
-- USER SESSIONS (REFRESH TOKEN STORAGE)
-- ============================================================
-- Purpose:
-- - Track active login sessions
-- - Enable logout (token revocation)
-- - Support multi-device login
-- - Store ONLY refresh tokens (NOT access tokens)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,

    -- relation
    user_id INT NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    -- SECURITY: store hashed refresh token only
    refresh_token_hash TEXT NOT NULL UNIQUE,

    -- optional metadata (useful for future debugging/security)
    user_agent TEXT,
    ip_address TEXT,

    -- lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Fast lookup by user (e.g., list all sessions)
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
ON user_sessions(user_id);

-- Fast lookup during authentication
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash
ON user_sessions(refresh_token_hash);


-- ============================================================
-- BOOKS TABLE (UPDATED)
-- ============================================================
-- Changes:
-- + file_type
-- + updated_at
-- + is_deleted (soft delete)
-- + file_size, page_count (metadata)
-- ============================================================

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,

    -- storage abstraction
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,         -- pdf, txt, etc.

    -- optional metadata
    file_size BIGINT,
    page_count INT,

    -- LLM generated
    summary TEXT,

    -- who uploaded
    uploaded_by INT REFERENCES users(id) ON DELETE SET NULL,

    -- async processing status
    status TEXT DEFAULT 'processing'
        CHECK (status IN ('processing', 'ready', 'failed')),

    -- soft delete
    is_deleted BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- normal index for title search (non-unique due to soft delete)
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);

-- uniqueness only for active (non-deleted) books per user
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_user_book_title
ON books (uploaded_by, title)
WHERE is_deleted = FALSE;


-- ============================================================
-- BORROWING (UPDATED - removed status)
-- ============================================================
-- Active borrow = returned_at IS NULL
-- ============================================================

CREATE TABLE IF NOT EXISTS user_books (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,

    borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    returned_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_books_user ON user_books(user_id);
CREATE INDEX IF NOT EXISTS idx_user_books_book ON user_books(book_id);

-- prevent duplicate active borrow
CREATE UNIQUE INDEX IF NOT EXISTS uniq_user_book_active
ON user_books(user_id, book_id)
WHERE returned_at IS NULL;


-- ============================================================
-- REVIEWS
-- ============================================================

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,

    content TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_book ON reviews(book_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_review_per_user_book
ON reviews(user_id, book_id);


-- ============================================================
-- BOOK REVIEW ANALYSIS
-- ============================================================

CREATE TABLE IF NOT EXISTS book_review_analysis (
    id SERIAL PRIMARY KEY,
    book_id INT UNIQUE NOT NULL REFERENCES books(id) ON DELETE CASCADE,

    summary TEXT,
    sentiment_score FLOAT,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- USER PREFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    preference_key TEXT NOT NULL,
    preference_score FLOAT DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_user_pref
ON user_preferences(user_id, preference_key);


-- ============================================================
-- MIGRATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
