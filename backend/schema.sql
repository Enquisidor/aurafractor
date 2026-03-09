-- Music Source Separation Tool - PostgreSQL Schema

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search on labels

-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) UNIQUE NOT NULL,
    app_version VARCHAR(20),
    subscription_tier VARCHAR(50) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'studio')),
    credits_balance INTEGER DEFAULT 100,
    credits_monthly_allowance INTEGER DEFAULT 100,
    credits_reset_date DATE,
    opt_in_training_data BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    
    CONSTRAINT valid_credits CHECK (credits_balance >= 0)
);

CREATE INDEX idx_users_device_id ON users(device_id);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Tracks table
CREATE TABLE tracks (
    track_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    duration_seconds INTEGER NOT NULL,
    sample_rate INTEGER DEFAULT 44100,
    format VARCHAR(20) NOT NULL CHECK (format IN ('mp3', 'wav', 'flac', 'ogg')),
    file_size_mb DECIMAL(10, 2),
    gcs_path VARCHAR(512) NOT NULL,
    genre_detected VARCHAR(100),
    tempo_detected INTEGER,
    spectral_hash VARCHAR(256),
    client_id VARCHAR(64),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,

    CONSTRAINT valid_duration CHECK (duration_seconds > 0)
);

CREATE INDEX idx_tracks_user_id ON tracks(user_id);
CREATE INDEX idx_tracks_uploaded_at ON tracks(uploaded_at);
CREATE INDEX idx_tracks_deleted_at ON tracks(deleted_at);
-- Partial unique index: one track per (user, client_id), NULLs excluded so legacy rows are unaffected
CREATE UNIQUE INDEX idx_tracks_user_client_id ON tracks(user_id, client_id) WHERE client_id IS NOT NULL;

-- Extractions table
CREATE TABLE extractions (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id UUID NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    job_id VARCHAR(255),
    sources_requested JSONB NOT NULL,  -- Array of {label, model, nlp_params, timestamps}
    processing_time_seconds INTEGER,
    credit_cost INTEGER NOT NULL,
    iteration_id UUID REFERENCES extractions(extraction_id) ON DELETE SET NULL,
    is_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    accepted_at TIMESTAMP NULL,
    
    CONSTRAINT valid_credit_cost CHECK (credit_cost > 0)
);

CREATE INDEX idx_extractions_track_id ON extractions(track_id);
CREATE INDEX idx_extractions_user_id ON extractions(user_id);
CREATE INDEX idx_extractions_status ON extractions(status);
CREATE INDEX idx_extractions_created_at ON extractions(created_at);
CREATE INDEX idx_extractions_job_id ON extractions(job_id);

-- Extraction results table
CREATE TABLE extraction_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    extraction_id UUID NOT NULL UNIQUE REFERENCES extractions(extraction_id) ON DELETE CASCADE,
    sources JSONB NOT NULL,  -- Array of {label, model_used, audio_url, waveform_url, size_mb}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extraction_results_extraction_id ON extraction_results(extraction_id);

-- Feedback table
CREATE TABLE feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    extraction_id UUID NOT NULL REFERENCES extractions(extraction_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    track_id UUID NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
    segment_start_seconds INTEGER NOT NULL,
    segment_end_seconds INTEGER NOT NULL,
    segment_label VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(50) NOT NULL CHECK (feedback_type IN ('too_much', 'too_little', 'artifacts', 'good')),
    feedback_detail VARCHAR(255),
    refined_label VARCHAR(255),
    comment TEXT,
    reextraction_id UUID REFERENCES extractions(extraction_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_segment CHECK (segment_start_seconds < segment_end_seconds)
);

CREATE INDEX idx_feedback_extraction_id ON feedback(extraction_id);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_track_id ON feedback(track_id);
CREATE INDEX idx_feedback_created_at ON feedback(created_at);

-- Training data table (anonymized)
CREATE TABLE training_data (
    training_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id_anon VARCHAR(8) NOT NULL,  -- Hash, not reversible
    original_label VARCHAR(255) NOT NULL,
    nlp_params JSONB,
    feedback_type VARCHAR(50),
    feedback_detail VARCHAR(255),
    refined_label VARCHAR(255),
    user_accepted BOOLEAN,
    genre VARCHAR(100),
    tempo INTEGER,
    is_ambiguous BOOLEAN,
    opt_in BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_labels CHECK (
        (original_label IS NOT NULL AND length(original_label) > 0) OR
        refined_label IS NOT NULL
    )
);

CREATE INDEX idx_training_data_user_anon ON training_data(user_id_anon);
CREATE INDEX idx_training_data_original_label ON training_data USING GIN (to_tsvector('english', original_label));
CREATE INDEX idx_training_data_opt_in ON training_data(opt_in);
CREATE INDEX idx_training_data_created_at ON training_data(created_at);

-- Session tokens table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(512) NOT NULL UNIQUE,
    refresh_token VARCHAR(512) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_session_token ON sessions(session_token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Instrument suggestions cache table
CREATE TABLE instrument_suggestions_cache (
    cache_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id UUID NOT NULL UNIQUE REFERENCES tracks(track_id) ON DELETE CASCADE,
    suggestions JSONB NOT NULL,  -- Array of {label, confidence, frequency_range, recommended}
    genre VARCHAR(100),
    tempo INTEGER,
    user_history_suggestions JSONB,  -- Array of strings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    CONSTRAINT suggestions_cache_ttl CHECK (expires_at > created_at)
);

CREATE INDEX idx_suggestions_cache_track_id ON instrument_suggestions_cache(track_id);
CREATE INDEX idx_suggestions_cache_expires_at ON instrument_suggestions_cache(expires_at);

-- Credit transactions log
CREATE TABLE credit_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    extraction_id UUID REFERENCES extractions(extraction_id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_created_at ON credit_transactions(created_at);

-- Views for common queries

-- User credit status view
CREATE VIEW user_credits_view AS
SELECT 
    u.user_id,
    u.subscription_tier,
    u.credits_balance,
    u.credits_monthly_allowance,
    u.credits_reset_date,
    COUNT(DISTINCT e.extraction_id) FILTER (WHERE e.created_at >= CURRENT_DATE) as extractions_this_month,
    COALESCE(SUM(e.credit_cost) FILTER (WHERE e.created_at >= CURRENT_DATE), 0) as credits_spent_this_month
FROM users u
LEFT JOIN extractions e ON u.user_id = e.user_id
WHERE u.deleted_at IS NULL
GROUP BY u.user_id, u.subscription_tier, u.credits_balance, u.credits_monthly_allowance, u.credits_reset_date;

-- Track extraction summary view
CREATE VIEW track_extraction_summary_view AS
SELECT 
    t.track_id,
    t.user_id,
    t.filename,
    t.uploaded_at,
    COUNT(DISTINCT e.extraction_id) as extractions_count,
    MAX(e.created_at) as latest_extraction_at,
    (SELECT JSON_BUILD_OBJECT(
        'extraction_id', e.extraction_id,
        'status', e.status,
        'completed_at', e.completed_at
    ) FROM extractions e 
    WHERE e.track_id = t.track_id 
    ORDER BY e.created_at DESC LIMIT 1) as latest_extraction
FROM tracks t
LEFT JOIN extractions e ON t.track_id = e.track_id
WHERE t.deleted_at IS NULL
GROUP BY t.track_id, t.user_id, t.filename, t.uploaded_at;
