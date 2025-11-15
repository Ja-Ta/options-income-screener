-- Migration: Add sentiment columns to picks table
-- Version: 2.7 (Sentiment Analysis Integration)
-- Date: 2025-11-15
-- Description: Adds sentiment context columns to picks table for sentiment-enhanced scoring

-- Add sentiment metrics to picks table
ALTER TABLE picks ADD COLUMN put_call_ratio REAL DEFAULT NULL;
ALTER TABLE picks ADD COLUMN cmf_20 REAL DEFAULT NULL;
ALTER TABLE picks ADD COLUMN sentiment_score REAL DEFAULT 0.5;
ALTER TABLE picks ADD COLUMN contrarian_signal TEXT DEFAULT 'none' CHECK(contrarian_signal IN ('long', 'short', 'none'));
ALTER TABLE picks ADD COLUMN days_to_cover REAL DEFAULT NULL;

-- Add index for filtering by contrarian signal
CREATE INDEX IF NOT EXISTS idx_picks_contrarian_signal ON picks(contrarian_signal);

-- Verification query (run after migration)
-- SELECT symbol, strategy, score, sentiment_score, contrarian_signal, put_call_ratio, cmf_20
-- FROM picks
-- WHERE asof = date('now')
-- ORDER BY score DESC
-- LIMIT 10;
