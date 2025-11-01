# Options Income Screener - MVP Implementation Roadmap

## ✅ Completed Foundation (Phase 1A)
- [x] Python 3.12 environment setup
- [x] Node.js dependencies
- [x] SQLite database with schema
- [x] Configuration management
- [x] Constants and parameters
- [x] Universe management
- [x] Utility modules (dates, math, logging)
- [x] Polygon client with mock data
- [x] Technical indicators
- [x] IV metrics calculations
- [x] Test scripts

## 🚀 Next Steps to Complete MVP (Phase 1B)

### 1. Screening Logic (Priority: HIGH)
**Files to implement:**
- `python_app/src/screeners/covered_calls.py`
- `python_app/src/screeners/cash_secured_puts.py`

**Key functions needed:**
```python
def select_cc_contract(options_chain, spot, delta_range, dte_range)
def screen_cc(symbol, price_data, options_chain, iv_metrics)
def select_csp_contract(options_chain, spot, delta_range, dte_range)
def screen_csp(symbol, price_data, options_chain, iv_metrics, earnings_date)
```

### 2. Scoring Algorithms (Priority: HIGH)
**Files to implement:**
- `python_app/src/scoring/score_cc.py`
- `python_app/src/scoring/score_csp.py`

**Key functions needed:**
```python
def cc_score(iv_rank, roi_30d, trend_strength, dividend_yield, below_200sma)
def csp_score(iv_rank, roi_30d, margin_of_safety, trend_stability)
```

### 3. Storage DAO Layer (Priority: HIGH)
**File to implement:**
- `python_app/src/storage/dao.py`

**Key classes needed:**
```python
class PicksDAO:
    def insert_pick(pick_dict) -> int
    def get_picks(asof, strategy=None, min_score=None)
    def insert_rationale(pick_id, summary)

class PricesDAO:
    def insert_prices(symbol, asof, price_data)
    def get_latest_prices(symbols)

class OptionsDAO:
    def insert_option_chain(symbol, asof, chain)
    def get_option_chain(symbol, asof)
```

### 4. Service Stubs (Priority: MEDIUM)
**Files to implement:**
- Update `python_app/src/services/telegram_service.py`
- Update `python_app/src/services/claude_service.py`

**Key functions needed:**
```python
# Telegram
def format_pick_telegram(pick, summary)
def send_telegram(message) -> bool

# Claude
def summarize_pick_with_claude(pick) -> str
```

### 5. Daily Job Pipeline (Priority: HIGH)
**File to implement:**
- `python_app/src/pipelines/daily_job.py`

**Main function:**
```python
def run_daily(asof: date):
    # 1. Load universe
    # 2. Fetch prices & compute features
    # 3. Fetch chains & compute IV
    # 4. Screen CC & CSP
    # 5. Score and rank
    # 6. Save to database
    # 7. Generate summaries
    # 8. Send alerts
```

### 6. Node.js API (Priority: MEDIUM)
**File to update:**
- `node_ui/src/server.js`

**Endpoints to implement:**
```javascript
GET /api/picks?date=YYYY-MM-DD&strategy=CC|CSP&minScore=0.5
GET /api/pick/:id
GET /api/health
```

## 📝 Implementation Order

### Day 1: Core Screening
1. Implement `covered_calls.py` screener
2. Implement `cash_secured_puts.py` screener
3. Implement scoring algorithms
4. Test with mock data

### Day 2: Data Persistence
1. Implement DAO layer
2. Test database operations
3. Implement daily job pipeline
4. Run end-to-end test

### Day 3: Services & UI
1. Implement service stubs
2. Update Node.js API
3. Test full workflow
4. Deploy test run

## 🧪 Testing Checklist

- [ ] Unit tests for screeners
- [ ] Unit tests for scoring
- [ ] Integration test for daily job
- [ ] API endpoint tests
- [ ] End-to-end workflow test

## 📊 Success Criteria

The MVP is complete when:
1. Daily job runs and produces picks
2. Picks are stored in database
3. API returns picks with filters
4. Mock summaries are generated
5. Test alerts can be sent

## 🔧 Quick Start Commands

```bash
# Activate Python environment
source python_app/venv/bin/activate

# Run daily job (mock mode)
python -m python_app.src.pipelines.daily_job

# Start Node.js server
cd node_ui && npm start

# Run tests
python test_foundation.py

# Check database
sqlite3 data/screener.db "SELECT * FROM picks LIMIT 5;"
```

## 📚 Key Files Reference

```
python_app/src/
├── config.py           # Environment config ✓
├── constants.py        # Screening parameters ✓
├── data/
│   └── polygon_client.py   # Market data (mock ready) ✓
├── features/
│   ├── technicals.py   # Technical indicators ✓
│   └── iv_metrics.py   # IV calculations ✓
├── screeners/
│   ├── covered_calls.py    # CC screening logic [TODO]
│   └── cash_secured_puts.py # CSP screening logic [TODO]
├── scoring/
│   ├── score_cc.py     # CC scoring [TODO]
│   └── score_csp.py    # CSP scoring [TODO]
├── storage/
│   ├── db.py          # Database connection ✓
│   ├── schema.sql     # Database schema ✓
│   └── dao.py         # Data access layer [TODO]
├── services/
│   ├── telegram_service.py  # Alerts [TODO]
│   └── claude_service.py    # Summaries [TODO]
└── pipelines/
    └── daily_job.py    # Main orchestration [TODO]
```

## 🎯 Next Action

Start with implementing the screening logic in:
1. `python_app/src/screeners/covered_calls.py`
2. `python_app/src/screeners/cash_secured_puts.py`

These are the core business logic components that everything else depends on.

---

**Note:** All components are designed to work with mock data initially. Once the MVP is working end-to-end with mock data, you can gradually replace with real API calls.