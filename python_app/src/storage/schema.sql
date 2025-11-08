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

CREATE INDEX IF NOT EXISTS idx_prices_asof ON prices(asof);
CREATE INDEX IF NOT EXISTS idx_options_symbol_asof ON options(symbol, asof);
CREATE INDEX IF NOT EXISTS idx_picks_asof ON picks(asof);
CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings(symbol);
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(earnings_date);
