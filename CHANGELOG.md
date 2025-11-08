# Changelog
All notable changes to the Options Income Screener project.

## [2.4.0] - 2025-11-08

### Added
- Stock Price column to web dashboard
  - Displays current stock price immediately after Symbol column
  - Format: $XXX.XX with proper decimal handling
  - Fallback to 'N/A' for missing data

### Changed
- Dashboard table layout now shows: Symbol → Stock Price → Strategy → Strike → Expiry → Premium → ROI → IV Rank → Score

---

## [2.3.0] - 2025-11-08

### Added
- **Earnings Calendar Integration** via Massive.com Benzinga API
  - Fetches next earnings date for each symbol (90-day lookahead)
  - Caches earnings data in database
  - Returns date, confirmation status, fiscal period, estimated EPS

- **Earnings Database Table**
  - Comprehensive schema with symbol, date, status, period, year, EPS
  - Indexed for fast lookups
  - Automated caching during daily screening

- **Risk-Based Earnings Penalties**
  - 4-tier penalty system for near-earnings picks
  - <7 days: -50% (SEVERE)
  - 7-14 days: -30% (STRONG)
  - 14-21 days: -15% (MODERATE)
  - 21-30 days: -7% (LIGHT)
  - Applied to both CC and CSP scoring

### Changed
- Updated `daily_job.py` to fetch and cache earnings data
- Enhanced CC and CSP scoring algorithms with earnings awareness
- Updated score explanation functions with earnings warnings

### Testing
- 100% success rate with 19 symbols
- 88 picks generated (46 CC, 42 CSP)
- Penalties verified: OGN (2 days) = 0.33 vs AXSM (no earnings) = 0.605

---

## [2.2.0] - 2025-11-02

### Fixed
- AI rationales not appearing in Telegram alerts
- Message truncation issues (split into 4 messages)
- IV Rank display bug (10000% → 100.0%)

### Added
- Expiry dates to Telegram alerts
- Legal disclaimer in alert footer
- Increased Claude API token limit (350 → 500)

### Changed
- Split combined alerts into header, CC picks, CSP picks, footer
- Each message stays under Telegram's 4096 character limit

---

## [2.1.0] - 2025-11-02

### Changed
- **API Migration**: Migrated from api.polygon.io → api.massive.com
- Removed artificial rate limits for unlimited tier
- Increased contract processing: 5 → 20 per strategy
- Reduced delays: 2s → 0.1s between symbols

### Added
- Expanded symbol universe: 13 → 19 symbols
- CSV-based universe management (`universe.csv`)
- New symbols: PLTR, COIN, NBIS, SOFI, HOOD, GME

### Performance
- 83% faster screening (31.7s for 19 symbols)
- 100% success rate on all symbols

---

## [2.0.0] - 2025-10-30

### Added
- Real options data integration via Polygon Options Advanced API
- Production screening with Greek-enhanced scoring
- SQLite database with WAL mode
- Web dashboard on DigitalOcean
- Telegram bot alerts with AI rationales
- Claude AI integration for pick explanations
- Automated cron scheduling (weekdays 10 AM ET)

### Features
- Covered Calls (CC) and Cash-Secured Puts (CSP) screening
- IV Rank and technical trend analysis
- Risk-adjusted scoring with Greeks (delta, theta, gamma, vega)
- Multi-destination Telegram alerts
- RESTful API with monitoring endpoints

---

## [1.0.0] - 2025-10-15

### Initial Release
- MVP implementation
- Mock data screening
- Basic scoring algorithms
- Console output
