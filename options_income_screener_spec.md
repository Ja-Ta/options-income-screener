# Options Income Screener — Technical Specification (Python + Polygon + SQLite + NodeJS + Telegram + Claude)
**Strategy Focus:** Covered Calls (CC) and Cash-Secured Puts (CSP) for a new investor building account value  
**Stack:** Python (ingest, screening, scoring), Polygon API (market/option data), SQLite (persistence), NodeJS (web UI), Telegram (alerts), Anthropic Claude API (summaries & explanations)

### 🐍 Python Environment

- **Version:** Python 3.12 (installed with Ubuntu 24.04 LTS)
- **Environment:** Local virtual environment (venv)
- **Policy:** All Python dependencies must explicitly support and be tested under **Python 3.12**.
- **Note:** No system-wide installs; all packages must be pinned in `python_app/requirements.txt`.
- **Verification:**  
  ```bash
  python3 --version  # → Python 3.12.x
  python3 -m venv python_app/venv
  source python_app/venv/bin/activate
  python -m pip install --upgrade pip

---

## 1) Goals & Non-Goals

### Goals
- Continuously screen a defined stock universe to surface **high-quality covered call and CSP candidates**.
- Enforce **liquidity, risk, and yield thresholds** suitable for a newer investor.
- Provide **explainable picks** with **plain-English rationales** via Claude.
- Deliver **daily alerts** (Telegram) and a **web dashboard** (NodeJS) with filters and historical logs.

### Non-Goals
- Not a brokerage/execution system.
- Not a high-frequency engine (daily/adhoc cadence is fine).

---

## 2) High-Level Architecture

```
+-------------------+        +--------------------+        +--------------------+
| Polygon API       | -----> | Python Ingest/ETL  | -----> | SQLite (WAL)       |
+-------------------+        +--------------------+        +--------------------+
                                    |   |                            |
                                    |   +--> Screening/Scoring       |
                                    |                                |
                                    v                                v
                            Claude Summaries                  NodeJS Web UI (read-only)
                                    |                                |
                                    +----------> Telegram Alerts <---+
```

- **Python**: ingestion, features, screening, scoring, DB writes.
- **NodeJS**: read-only dashboard on SQLite.
- **Telegram bot**: concise daily alerts.
- **Claude**: short, human-readable rationale per pick.

Cadence: run daily after market close (configurable), plus ad-hoc runs.

---

## 3) Repository & Folder Structure

```
options-income-screener/
├─ README.md
├─ .env.example
├─ infra/
│  └─ nginx.conf                # optional reverse proxy
├─ python_app/
│  ├─ pyproject.toml / requirements.txt
│  ├─ src/
│  │  ├─ config.py
│  │  ├─ constants.py
│  │  ├─ utils/
│  │  │  ├─ dates.py
│  │  │  ├─ math.py
│  │  │  └─ logging.py
│  │  ├─ data/
│  │  │  ├─ polygon_client.py
│  │  │  ├─ ingest_universe.py
│  │  │  └─ option_chain.py
│  │  ├─ features/
│  │  │  ├─ iv_metrics.py
│  │  │  ├─ technicals.py
│  │  │  └─ earnings_calendar.py
│  │  ├─ screeners/
│  │  │  ├─ covered_calls.py
│  │  │  └─ cash_secured_puts.py
│  │  ├─ scoring/
│  │  │  ├─ score_cc.py
│  │  │  └─ score_csp.py
│  │  ├─ storage/
│  │  │  ├─ db.py
│  │  │  ├─ schema.sql
│  │  │  └─ dao.py
│  │  ├─ services/
│  │  │  ├─ telegram_service.py
│  │  │  ├─ claude_service.py
│  │  │  └─ scheduler.py
│  │  ├─ pipelines/
│  │  │  ├─ daily_job.py
│  │  │  └─ adhoc_run.py
│  │  └─ api/
│  │     └─ fastapi_app.py      # optional: /healthz, /run
│  └─ tests/
│     ├─ test_iv_metrics.py
│     ├─ test_screeners.py
│     └─ test_scoring.py
├─ node_ui/
│  ├─ package.json
│  ├─ src/
│  │  ├─ server.ts              # Express (or Next.js alternative)
│  │  ├─ db.ts                  # read-only sqlite
│  │  ├─ routes/
│  │  │  └─ api.ts
│  │  ├─ pages/
│  │  │  ├─ index.tsx
│  │  │  └─ picks/[date].tsx
│  │  └─ components/
│  │     ├─ Table.tsx
│  │     ├─ Filters.tsx
│  │     └─ Badges.tsx
└─ data/
   ├─ screener.db               # SQLite file (volume)
   └─ logs/
```

---

## 4) Environment & Secrets

`.env.example`:
```
POLYGON_API_KEY=...
ANTHROPIC_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=123456789
DATABASE_URL=sqlite:///data/screener.db
MARKET_TIMEZONE=America/New_York
SCREENER_RUN_HOUR=18
UNIVERSE_FILE=python_app/src/data/universe.csv
```

SQLite PRAGMAs (on engine init):
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

---

## 5) Database Schema (SQLite)

```sql
-- Symbols tracked
CREATE TABLE IF NOT EXISTS symbols (
  symbol TEXT PRIMARY KEY,
  name TEXT,
  sector TEXT,
  is_active INTEGER DEFAULT 1,
  last_seen DATE
);

-- Daily price snapshots
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

-- Option chain snapshot (subset)
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

-- IV aggregates
CREATE TABLE IF NOT EXISTS iv_metrics (
  symbol TEXT,
  asof DATE,
  iv_rank REAL,
  iv_percentile REAL,
  PRIMARY KEY (symbol, asof)
);

-- Earnings calendar (optional if sourced)
CREATE TABLE IF NOT EXISTS earnings (
  symbol TEXT,
  earnings_date DATE,
  confirmed INTEGER
);

-- Screener output (top candidates)
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
  notes TEXT
);

-- Anthropic summaries (rationales)
CREATE TABLE IF NOT EXISTS rationales (
  pick_id INTEGER,
  summary TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (pick_id) REFERENCES picks(id)
);

-- Alert audit
CREATE TABLE IF NOT EXISTS alerts (
  pick_id INTEGER,
  channel TEXT,
  status TEXT,
  sent_at DATETIME,
  error TEXT
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_prices_asof ON prices(asof);
CREATE INDEX IF NOT EXISTS idx_options_symbol_asof ON options(symbol, asof);
CREATE INDEX IF NOT EXISTS idx_picks_asof ON picks(asof);
```

---

## 6) Screening & Scoring Rules

### A) Covered Calls (CC)

**Pre-filters**
- Price ≥ $10  
- Option liquidity: OI ≥ 500; option volume ≥ 50; bid-ask spread ≤ 10% of mid  
- Trend: `sma20 > sma50` and `close ≥ sma200` (flag 🟡 if below SMA200; allow but down-weighted)  
- Volatility sanity: `hv_60 ≤ 0.50` (adjustable)  
- IV environment: `iv_rank ≥ 40%`

**Contract selection**
- DTE: 30–45 days  
- Call delta: 0.25–0.35  
- Choose the contract maximizing `ROI_30d = premium / close` subject to liquidity & spread filters.

**Score (example)**
```
Trend_Strength = zscore( (sma20 - sma50) / close )
CC_Score = 0.40*z(IV_Rank) + 0.30*ROI_30d + 0.20*Trend_Strength + 0.10*Dividend_Yield
Downtrend penalty: if close < sma200, multiply score by 0.85
Target: annualized ROI ≥ 15% (i.e., ROI_30d * 12 ≥ 0.15)
```

### B) Cash-Secured Puts (CSP)

**Pre-filters**
- Price ≥ $10  
- IV environment: `iv_rank ≥ 50%`  
- Earnings exclusion: skip if within 10 calendar days of earnings  
- (Optional) Fundamentals if sourced: positive TTM EPS, Net Debt/EBITDA < 3

**Contract selection**
- Put delta: 0.25–0.30 (≈ 5–10% OTM)  
- DTE: 30–45 days  
- Choose contract maximizing `ROI_30d = premium / strike` with liquidity checks.

**Score (example)**
```
Margin_of_Safety = (spot - strike) / spot
Trend_Stability  = 1 - std( daily_returns, 20d )
CSP_Score = 0.40*IV_Rank + 0.30*ROI_30d + 0.20*Margin_of_Safety + 0.10*Trend_Stability
Target: annualized ROI ≥ 12% (ROI_30d * 12 ≥ 0.12)
```

---

## 7) Python Pseudocode (Claude-ready)

### 7.1 `config.py`
```python
import os

POLYGON_API_KEY   = os.getenv("POLYGON_API_KEY")
DB_URL            = os.getenv("DATABASE_URL", "sqlite:///data/screener.db")
MARKET_TZ         = os.getenv("MARKET_TIMEZONE", "America/New_York")
RUN_HOUR          = int(os.getenv("SCREENER_RUN_HOUR", "18"))
UNIVERSE_FILE     = os.getenv("UNIVERSE_FILE", "python_app/src/data/universe.csv")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
```

### 7.2 `data/polygon_client.py`
```python
from datetime import date
from typing import List, Dict, Any

class PolygonClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # init HTTP session with retries/backoff

    def get_universe(self) -> List[str]:
        # load universe.csv e.g., S&P500 + high options volume names
        # return ["AAPL","MSFT",...]
        ...

    def get_daily_prices(self, symbols: List[str], asof: date) -> Dict[str, Dict[str, Any]]:
        # fetch close, volume; compute SMA20/50/200, HV20/60 locally
        ...

    def get_option_chain(self, symbol: str, asof: date) -> List[Dict[str, Any]]:
        # fetch nearest expiries around 30–45 DTE including greeks, iv, oi, volume
        # return list of {side, strike, expiry, bid, ask, mid, delta, iv, oi, vol, dte}
        ...

    def get_earnings(self, symbol: str):
        # optional: earnings date if available, else None
        ...
```

### 7.3 `features/technicals.py`
```python
import numpy as np
def sma(x, n): ...
def hist_vol(returns, n): ...
def trend_strength(close, sma20, sma50):
    # e.g., normalized slope of (sma20 - sma50)/close
    ...
```

### 7.4 `features/iv_metrics.py`
```python
def iv_rank(today_iv, trailing_1y_iv_series) -> float: ...
def iv_percentile(today_iv, trailing_1y_iv_series) -> float: ...
```

### 7.5 `screeners/covered_calls.py`
```python
def select_cc_contract(options_chain, spot):
    # filter calls: 30≤DTE≤45, 0.25≤Δ≤0.35, OI≥500, Vol≥50, spread≤10% mid
    # return best by ROI_30d, with dict fields used downstream
    ...

def screen_cc(symbol_row, options_chain, ivr, hv60, smas):
    # apply prefilters; compute ROI_30d=premium/spot; score via score_cc()
    # return pick dict or None
    ...
```

### 7.6 `screeners/cash_secured_puts.py`
```python
def select_csp_contract(options_chain, spot):
    # filter puts: 30≤DTE≤45, 0.25≤Δ≤0.30, OI≥500, Vol≥50, spread≤10% mid
    ...

def screen_csp(symbol_row, options_chain, ivr, hv60, smas, earnings_date):
    # earnings exclusion ±10d; compute ROI_30d=premium/strike; score via score_csp()
    # return pick dict or None
    ...
```

### 7.7 `scoring/score_cc.py` & `scoring/score_csp.py`
```python
def z(x, mu, sigma): return 0 if sigma == 0 else (x - mu) / sigma

def cc_score(iv_rank, roi_30d, trend_strength, dividend_yield=0.0, below_200sma=False):
    base = 0.40*z(iv_rank, 50, 15) + 0.30*roi_30d + 0.20*trend_strength + 0.10*dividend_yield
    return base * (0.85 if below_200sma else 1.0)

def csp_score(iv_rank, roi_30d, margin_of_safety, trend_stability):
    return 0.40*(iv_rank/100) + 0.30*roi_30d + 0.20*margin_of_safety + 0.10*trend_stability
```

### 7.8 `storage/db.py` & `storage/dao.py`
```python
from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///data/screener.db", connect_args={"check_same_thread": False})
with engine.connect() as con:
    con.execute(text("PRAGMA journal_mode=WAL;"))
    con.execute(text("PRAGMA synchronous=NORMAL;"))

class PicksDAO:
    def insert_pick(self, pick: dict) -> int: ...
    def insert_rationale(self, pick_id: int, summary: str): ...
    def fetch_top_picks(self, asof): ...
```

### 7.9 `services/claude_service.py`
```python
CLAUDE_PROMPT = """You are an options mentor. Summarize this pick for a newer investor (≤120 words).
Explain why it's attractive, key risks, and when to re-evaluate. Use plain English.
DATA:
{pick_json}
"""

def summarize_pick_with_claude(pick: dict) -> str:
    # call Anthropic API (e.g., "claude-3-7-sonnet-latest")
    # ensure we only summarize provided fields
    ...
```

### 7.10 `services/telegram_service.py`
```python
def format_pick_telegram(pick, summary):
    line1 = f"[{pick['asof']}] {pick['strategy']} {pick['symbol']}"
    line2 = f"{pick['selected_option']}  ROI30d: {pick['roi_30d']:.2%}  IVR: {int(round(pick['ivr']))}%  Score: {pick['score']:.2f}"
    lines = [line1, line2, f"Notes: {pick.get('notes','-')}", f"Summary: {summary}"]
    return "\n".join(lines)

def send_telegram(message: str) -> bool:
    # POST to Telegram sendMessage with chat_id & text
    ...
```

### 7.11 `pipelines/daily_job.py`
```python
from datetime import date

def run_daily(asof: date):
    # 1) load universe
    # 2) fetch prices -> compute SMA/HV
    # 3) fetch chains -> compute IV rank/percentile
    # 4) screen CC & CSP -> choose contracts -> compute ROI & Score
    # 5) write picks; call Claude -> write rationales
    # 6) alert top N via Telegram
    # 7) log stats, handle errors
    ...
```

### 7.12 `services/scheduler.py`
```python
from apscheduler.schedulers.blocking import BlockingScheduler

def schedule_daily(run_hour_local=18):
    # cron-like schedule at run_hour_local in MARKET_TZ
    ...
```

---

## 8) NodeJS Web UI (Express or Next.js)

**Endpoints**
- `GET /api/picks?date=YYYY-MM-DD&strategy=CC|CSP&minScore=...&minIVR=...&minROI=...`
- `GET /api/pick/:id` → pick detail + rationale
- `GET /healthz`

**DB (read-only)**
- Use `better-sqlite3` or `sqlite3` with file mounted read-only.
- Queries:
  - Latest date: `SELECT MAX(asof) FROM picks;`
  - Picks page: filter by query params; order by score DESC.

**UI**
- Filters: Date, Strategy, Min ROI, Min IVR, Min Score, Liquidity flags.
- Table columns: Symbol, Strategy, IVR, ROI(30d), Strike/Expiry, Score, Badges.
- Badges: 🟢 trend ok, 🟡 below SMA200, 🔴 earnings soon, 💧 illiquid.
- Row click → Drawer with: contract details, ROI calc, IV rank, Claude rationale, mini sparkline (60d close).

---

## 9) Alerts

- Trigger after `run_daily()` completes.
- Select top N per strategy where `score ≥ threshold`.
- Deduplicate same-day alerts using `alerts` table.
- Message text comes from `format_pick_telegram()`; include dashboard deep link if applicable.

---

## 10) Operational Concerns

- **Timezones:** Normalize to `MARKET_TIMEZONE` and store `asof` as date.
- **Earnings risk:** Enforce exclusion window (±10 days, configurable).
- **DB concurrency:** WAL mode; short transactions; Node uses read-only.
- **Rate limits:** Batch symbol requests, cache option chains, retry with backoff.
- **Observability:** Simple file logging to `data/logs/`; optional FastAPI `/healthz`.
- **Testing:** Unit tests for IV rank, SMA/HV, scoring, contract selection paths.
- **Resilience:** If IV missing, skip symbol; if Telegram fails, record `alerts.status='error'`.

---

## 11) Deployment on DigitalOcean Droplet (no Docker)

**Target:** Ubuntu 24.04 LTS Droplet (2 vCPU / 4GB RAM recommended), IPv4, SSH key auth enabled.

### 11.1 System setup

```bash
adduser app
usermod -aG sudo app
su - app

sudo apt update && sudo apt -y upgrade
sudo apt -y install build-essential git ufw nginx sqlite3 python3.11 python3.11-venv python3-pip \
                    nodejs npm certbot python3-certbot-nginx

sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

> If Node 20 LTS isn’t available via apt, install nvm and `nvm install 20`.

### 11.2 Directory layout

```
/opt/options-income-screener/
├─ python_app/
│  ├─ venv/
│  └─ src/
├─ node_ui/
│  ├─ build/
└─ data/
   ├─ screener.db
   └─ logs/
```

```bash
sudo mkdir -p /opt/options-income-screener/{python_app,node_ui,data/logs}
sudo chown -R app:app /opt/options-income-screener
```

### 11.3 Environment variables

```bash
sudo mkdir -p /etc/options-income-screener
sudo chown app:app /etc/options-income-screener
nano /etc/options-income-screener/.env
```

```
POLYGON_API_KEY=...
ANTHROPIC_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=123456789
DATABASE_URL=sqlite:////opt/options-income-screener/data/screener.db
MARKET_TIMEZONE=America/New_York
SCREENER_RUN_HOUR=18
UNIVERSE_FILE=/opt/options-income-screener/python_app/src/data/universe.csv
```

```bash
chmod 600 /etc/options-income-screener/.env
```

### 11.4 Install app code

```bash
cd /opt/options-income-screener
git clone <your-repo-url> repo

# Python
python3 -m venv python_app/venv
source python_app/venv/bin/activate
pip install --upgrade pip
pip install -r repo/python_app/requirements.txt
deactivate
rsync -a repo/python_app/src/ python_app/src/

# Node
rsync -a repo/node_ui/ node_ui/
cd node_ui
npm ci
npm run build
```

Initialize SQLite and PRAGMAs:

```bash
sqlite3 /opt/options-income-screener/data/screener.db <<'SQL'
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
.read /opt/options-income-screener/python_app/src/storage/schema.sql
SQL
```

### 11.5 Services (systemd)

**Option A (recommended): systemd timer (one-shot daily)**

`/etc/systemd/system/options-screener-daily.service`
```ini
[Unit]
Description=Options Screener Daily Run (one-shot)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=app
Group=app
EnvironmentFile=/etc/options-income-screener/.env
WorkingDirectory=/opt/options-income-screener/python_app
ExecStart=/opt/options-income-screener/python_app/venv/bin/python -m src.pipelines.daily_job
Nice=5
IOSchedulingClass=best-effort
```

`/etc/systemd/system/options-screener-daily.timer`
```ini
[Unit]
Description=Run Options Screener once per day (18:05 local)

[Timer]
OnCalendar=*-*-* 18:05:00
Persistent=true
Unit=options-screener-daily.service

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now options-screener-daily.timer
sudo systemctl start options-screener-daily.service
journalctl -u options-screener-daily.service -n 200 --no-pager
```

**Alternative Option B: long-running worker (APScheduler)**

`/etc/systemd/system/options-screener-worker.service`
```ini
[Unit]
Description=Options Screener Worker (APScheduler inside)
After=network-online.target
Wants=network-online.target

[Service]
User=app
Group=app
EnvironmentFile=/etc/options-income-screener/.env
WorkingDirectory=/opt/options-income-screener/python_app
ExecStart=/opt/options-income-screener/python_app/venv/bin/python -m src.services.scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now options-screener-worker.service
```

**Node UI service**

`/etc/systemd/system/options-screener-ui.service`
```ini
[Unit]
Description=Options Screener Node UI
After=network-online.target
Wants=network-online.target

[Service]
User=app
Group=app
Environment=NODE_ENV=production
WorkingDirectory=/opt/options-income-screener/node_ui
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now options-screener-ui.service
journalctl -u options-screener-ui.service -n 100 --no-pager
```

### 11.6 Nginx reverse proxy + TLS

`/etc/nginx/sites-available/options-screener`
```nginx
server {
    listen 80;
    server_name your.domain.com;

    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    client_max_body_size 10m;
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
}
```

Enable and issue a cert:

```bash
sudo ln -s /etc/nginx/sites-available/options-screener /etc/nginx/sites-enabled/options-screener
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your.domain.com --redirect -n --agree-tos -m you@example.com
```

### 11.7 Backups (SQLite)

`/usr/local/bin/backup-screener.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +'%Y%m%d_%H%M%S')
SRC="/opt/options-income-screener/data/screener.db"
DST="/opt/options-income-screener/data/backups/screener_${STAMP}.db"
mkdir -p /opt/options-income-screener/data/backups
sqlite3 "$SRC" ".backup '$DST'"
find /opt/options-income-screener/data/backups -type f -mtime +30 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-screener.sh
(crontab -e)
20 2 * * * /usr/local/bin/backup-screener.sh >> /opt/options-income-screener/data/logs/backup.log 2>&1
```

### 11.8 Log rotation

`/etc/logrotate.d/options-screener`
```
/opt/options-income-screener/data/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

### 11.9 Zero-downtime deploy

```bash
cd /opt/options-income-screener
git fetch --all && git checkout <tag-or-branch> && git pull
# Python deps
source python_app/venv/bin/activate
pip install -r repo/python_app/requirements.txt
deactivate
rsync -a repo/python_app/src/ python_app/src/
# Node build (if UI changed)
cd node_ui && npm ci && npm run build
# restart services
sudo systemctl restart options-screener-ui.service
# for timer-based runs, no restart needed; for worker:
# sudo systemctl restart options-screener-worker.service
```

### 11.10 Monitoring & health

- Check services: `systemctl status options-screener-daily.service`, `...-ui.service`, or `...-worker.service`.  
- Logs: `journalctl -u <service> -f`.  
- Optional **FastAPI** `/healthz` endpoint in Python if you enabled `fastapi_app.py` and proxied it.

### 11.11 Security notes

- SSH keys only; disable password login (`PasswordAuthentication no`).  
- Keep OS patched (`unattended-upgrades`).  
- Protect `.env` (0600), DB (app-owned), and ensure Node runs read-only against the DB.  
- Rate-limit Nginx if you expose any API routes publicly.

---

## 12) End-to-End Flow

1. `scheduler.py` triggers `run_daily()` at 18:00 ET.
2. Python pulls prices/options, computes SMA/HV and IV ranks.
3. CC & CSP screeners choose contracts and compute ROI/Score.
4. Picks saved; Claude generates rationales; rationales saved.
5. Telegram sends top 5 per strategy above thresholds.
6. Dashboard renders latest date by default.

---

## 13) Acceptance Criteria

- Daily run yields ≥ 5 candidates across CC/CSP in normal markets.  
- Dashboard filter latency < 200 ms for 1k picks.  
- Telegram alerts delivered for qualifying picks.  
- Claude summaries ≤ 120 words, accurate to data provided.

---

## 14) Configuration Defaults

```
MIN_PRICE = 10.0
MIN_OI = 500
MIN_VOL = 50
MAX_SPREAD_PCT = 0.10
CC_DELTA_RANGE = (0.25, 0.35)
CSP_DELTA_RANGE = (0.25, 0.30)
DTE_RANGE = (30, 45)
CC_MIN_IVR = 40
CSP_MIN_IVR = 50
EARNINGS_EXCLUSION_DAYS = 10
CC_ANNUALIZED_TARGET = 0.15
CSP_ANNUALIZED_TARGET = 0.12
TOP_N_ALERTS_PER_STRATEGY = 5
SCORE_THRESHOLD = 0.50
```

---

## 15) Claude Prompt Template (exact)

```
System: You are an options mentor for newer investors. Be concise, accurate, and plain-English.

User:
Summarize this options income pick in ≤120 words.
Explain why it’s attractive, list key risks, and when to re-evaluate.
Do not invent data—use only the JSON provided.

JSON:
{pick_json}
```

---

## 16) Sample Telegram Payload

```
[2025-10-28] CC AAPL
CALL 2025-11-22 Δ≈0.30 @ $200  ROI30d: 1.15%  IVR: 47%  Score: 0.82
Notes: 🟢 trend ok; spread 6%; OI>1k
Summary: (Claude’s 2–3 sentence rationale)
```

---

## 17) Node UI Query Examples

- Latest picks:
```sql
SELECT * FROM picks WHERE asof=(SELECT MAX(asof) FROM picks) ORDER BY score DESC LIMIT 200;
```

- Filtered:
```sql
SELECT * FROM picks
WHERE asof=? AND strategy=?
  AND iv_rank >= ?
  AND roi_30d >= ?
  AND score >= ?
ORDER BY score DESC
LIMIT 500;
```

---

## 18) Error Handling & Retries

- **Polygon**: exponential backoff, respect rate limits; partial results allowed with symbol-level skips logged.
- **Claude**: on failure, store pick without rationale; retry once; log.
- **Telegram**: catch HTTP errors; write `alerts(status='error')` with response text.

---

## 19) Security & Keys

- Keep keys in `.env`; never commit.  
- Limit Node to read-only DB file (filesystem perms).  
- Sanitize query params (prepared statements).

---

## 20) Testing Plan

- **Unit**: SMA/HV, IV Rank, contract filters, ROI math, scoring.  
- **Integration**: end-to-end run on tiny universe mock with recorded fixtures.  
- **Contract**: API route response shape; UI renders with empty vs. populated states.

---

## 21) Future Enhancements

- Wheel strategy tracker (CSP assignment → CC selling).  
- Portfolio risk budget (beta-weighted deltas).  
- Opt-in earnings capture with tighter spread thresholds.  
- Backtesting harness with P&L series export.
