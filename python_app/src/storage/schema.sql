-- See spec for details
CREATE TABLE IF NOT EXISTS symbols (
  symbol TEXT PRIMARY KEY,
  name TEXT,
  sector TEXT,
  is_active INTEGER DEFAULT 1,
  last_seen DATE
);

CREATE TABLE IF NOT EXISTS prices (
  symbol TEXT,
  asof DATE,
  close REAL,
  volume INTEGER,
  sma20 REAL,
  sma50 REAL,
  sma200 REAL,
  hv_20 REAL,
  hv_60 REAL,
  PRIMARY KEY (symbol, asof)
);

CREATE TABLE IF NOT EXISTS options (
  symbol TEXT,
  asof DATE,
  expiry DATE,
  side TEXT CHECK(side IN ('call','put')),
  strike REAL,
  bid REAL,
  ask REAL,
  mid REAL,
  delta REAL,
  iv REAL,
  oi INTEGER,
  vol INTEGER,
  dte INTEGER,
  PRIMARY KEY (symbol, asof, expiry, side, strike)
);

CREATE TABLE IF NOT EXISTS iv_metrics (
  symbol TEXT,
  asof DATE,
  iv_rank REAL,
  iv_percentile REAL,
  PRIMARY KEY (symbol, asof)
);

CREATE TABLE IF NOT EXISTS earnings (
  symbol TEXT NOT NULL,
  earnings_date DATE NOT NULL,
  date_status TEXT,
  fiscal_period TEXT,
  fiscal_year INTEGER,
  estimated_eps REAL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, earnings_date)
);

CREATE TABLE IF NOT EXISTS picks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asof DATE,
  symbol TEXT,
  strategy TEXT CHECK(strategy IN ('CC','CSP')),
  selected_option TEXT,
  strike REAL,
  expiry DATE,
  premium REAL,
  roi_30d REAL,
  iv_rank REAL,
  score REAL,
  dividend_yield REAL DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS rationales (
  pick_id INTEGER,
  summary TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (pick_id) REFERENCES picks(id)
);

CREATE TABLE IF NOT EXISTS alerts (
  pick_id INTEGER,
  channel TEXT,
  status TEXT,
  sent_at DATETIME,
  error TEXT
);

-- Sentiment metrics cache (v2.7 - Sentiment Analysis Integration)
CREATE TABLE IF NOT EXISTS sentiment_metrics (
  symbol TEXT NOT NULL,
  asof DATE NOT NULL,

  -- Put/Call ratio metrics
  put_call_ratio_volume REAL,
  put_call_ratio_oi REAL,
  total_call_volume INTEGER,
  total_put_volume INTEGER,
  total_call_oi INTEGER,
  total_put_oi INTEGER,

  -- Chaikin Money Flow
  cmf_20 REAL,

  -- Short interest (placeholder for future)
  days_to_cover REAL,
  short_pct_float REAL,

  -- Derived sentiment signals
  sentiment_extreme TEXT CHECK(sentiment_extreme IN ('negative', 'positive', 'neutral')),
  contrarian_signal TEXT CHECK(contrarian_signal IN ('long', 'short', 'none')),
  sentiment_score REAL,
  sentiment_rank INTEGER,

  -- Metadata
  data_quality TEXT CHECK(data_quality IN ('complete', 'partial', 'insufficient')),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (symbol, asof)
);

-- Universe scan log (tracks daily sentiment scanning and filtering)
CREATE TABLE IF NOT EXISTS universe_scan_log (
  run_date DATE NOT NULL,
  symbol TEXT NOT NULL,

  -- Scan results
  scanned INTEGER DEFAULT 1,
  passed_sentiment_filter INTEGER DEFAULT 0,
  sentiment_score REAL,
  sentiment_rank INTEGER,
  contrarian_signal TEXT,

  -- Filter decision
  exclusion_reason TEXT,
  included_in_screening INTEGER DEFAULT 0,

  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (run_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_prices_asof ON prices(asof);
CREATE INDEX IF NOT EXISTS idx_options_symbol_asof ON options(symbol, asof);
CREATE INDEX IF NOT EXISTS idx_picks_asof ON picks(asof);
CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings(symbol);
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(earnings_date);
CREATE INDEX IF NOT EXISTS idx_sentiment_asof ON sentiment_metrics(asof);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol ON sentiment_metrics(symbol);
CREATE INDEX IF NOT EXISTS idx_sentiment_signal ON sentiment_metrics(contrarian_signal);
CREATE INDEX IF NOT EXISTS idx_universe_scan_date ON universe_scan_log(run_date);
CREATE INDEX IF NOT EXISTS idx_universe_scan_passed ON universe_scan_log(passed_sentiment_filter);
