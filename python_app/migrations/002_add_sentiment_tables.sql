-- Migration 002: Add sentiment analysis tables
-- Version: 2.7
-- Purpose: Create tables for sentiment metrics and universe scan logging

-- Sentiment metrics table - stores daily sentiment analysis for each symbol
CREATE TABLE IF NOT EXISTS sentiment_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asof DATE NOT NULL,
    symbol TEXT NOT NULL,
    put_call_ratio_volume REAL,
    put_call_ratio_oi REAL,
    cmf_20 REAL,
    sentiment_score REAL NOT NULL DEFAULT 0.5,
    sentiment_rank INTEGER,
    contrarian_signal TEXT NOT NULL DEFAULT 'none' CHECK(contrarian_signal IN ('long', 'short', 'none')),
    data_quality TEXT NOT NULL DEFAULT 'full' CHECK(data_quality IN ('full', 'partial', 'minimal')),
    days_to_cover REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asof, symbol)
);

-- Index for fast lookups by date and signal
CREATE INDEX IF NOT EXISTS idx_sentiment_metrics_asof ON sentiment_metrics(asof);
CREATE INDEX IF NOT EXISTS idx_sentiment_metrics_signal ON sentiment_metrics(contrarian_signal);
CREATE INDEX IF NOT EXISTS idx_sentiment_metrics_rank ON sentiment_metrics(sentiment_rank);

-- Universe scan log - tracks daily sentiment filtering decisions
CREATE TABLE IF NOT EXISTS universe_scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    contrarian_signal TEXT NOT NULL DEFAULT 'none',
    put_call_ratio REAL,
    cmf_20 REAL,
    sentiment_score REAL,
    sentiment_rank INTEGER,
    passed_sentiment_filter INTEGER NOT NULL DEFAULT 0 CHECK(passed_sentiment_filter IN (0, 1)),
    filter_reason TEXT,
    data_quality TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_date, symbol)
);

-- Index for fast filtering analysis
CREATE INDEX IF NOT EXISTS idx_universe_scan_date ON universe_scan_log(run_date);
CREATE INDEX IF NOT EXISTS idx_universe_scan_passed ON universe_scan_log(passed_sentiment_filter);
CREATE INDEX IF NOT EXISTS idx_universe_scan_signal ON universe_scan_log(contrarian_signal);
