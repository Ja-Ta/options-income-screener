# Massive.com API Usage Summary
**Generated:** November 2, 2025
**Purpose:** Document all API endpoints used by Options Income Screener

---

## Overview

The Options Income Screener uses **4 Massive.com API endpoints** for market data:

1. **Stock Prices** (`/v2/aggs/ticker/{ticker}/prev`)
2. **Options Contracts List** (`/v3/reference/options/contracts`)
3. **Option Quotes** (`/v3/quotes/{optionsTicker}`)
4. **Option Snapshots** (`/v3/snapshot/options/{underlying}/{contract}`)

---

## API Call Breakdown Per Symbol

For each symbol screened (e.g., SPY, AAPL, etc.):

| Endpoint | Calls Per Symbol | Purpose |
|----------|------------------|---------|
| Stock Price | 1 | Get current stock price |
| Options Contracts | 2 | List available calls (1) and puts (1) |
| Option Quotes | 40 | Get bid/ask for 20 calls + 20 puts |
| Option Snapshots | 40 | Get Greeks & IV for 20 calls + 20 puts |
| **TOTAL** | **83** | Total API calls per symbol |

---

## Full Screening Run (19 Symbols)

### Total API Calls
- **Stock Prices:** 19 calls (1 per symbol)
- **Options Contracts:** 38 calls (2 per symbol)
- **Option Quotes:** 760 calls (40 per symbol)
- **Option Snapshots:** 760 calls (40 per symbol)
- **TOTAL:** 1,577 Massive.com API calls per screening run

### Time Pattern
- With current 0.1s delays between symbols: ~2-3 minutes
- Without delays (if rate limits allow): ~30-60 seconds

---

## Rate Limit Issues Observed

### Current Problem
When running full 19-symbol screening, we hit **429 "Too Many Requests"** errors after processing ~5 symbols (~415 API calls in ~10 seconds).

### Error Message
```
"You've exceeded the maximum requests per minute, please wait or upgrade your subscription"
```

### Symptoms
- First 5 symbols: Success (SPY, QQQ, IWM, DIA, AAPL)
- Remaining 14 symbols: Failed with 429 errors
- Failure point: ~10 seconds into screening, after ~415 API calls

---

## API Tier Requirements

Based on Massive.com documentation and our usage:

| Endpoint | Minimum Tier | Notes |
|----------|--------------|-------|
| `/v2/aggs/ticker/{ticker}/prev` | **Basic** | Stock prices available in all tiers |
| `/v3/reference/options/contracts` | **Options Starter** | Options contract listings |
| `/v3/quotes/{optionsTicker}` | **Options Starter** | Real-time option quotes |
| `/v3/snapshot/options/{underlying}/{contract}` | **Options Advanced** | Greeks & IV data (REQUIRED) |

**Project Requirement:** Minimum **Options Advanced** tier (for Greeks/IV in snapshots)

---

## Questions to Verify in Massive.com Dashboard

Please check your account dashboard at https://polygon.io/dashboard or https://massive.com/dashboard:

### 1. Account Tier
- [ ] What is your current subscription tier?
  - Basic
  - Starter
  - Options Starter
  - **Options Advanced** ← Required
  - Options Pro

### 2. Rate Limits
Check the limits for your tier:

- [ ] **Requests per minute:** _____________
- [ ] **Requests per second:** _____________
- [ ] **Concurrent requests:** _____________
- [ ] **Daily API calls:** _____________

### 3. Endpoint Access
Verify you have access to:

- [ ] `/v2/aggs` - Stock aggregates
- [ ] `/v3/reference/options/contracts` - Options listings
- [ ] `/v3/quotes` - Real-time option quotes
- [ ] `/v3/snapshot/options` - Option Greeks & IV (CRITICAL)

### 4. Usage Statistics
Check your current usage:

- [ ] API calls today: _____________
- [ ] API calls this month: _____________
- [ ] Percentage of limit used: _____________%

---

## Recommendations

Based on 429 errors, we need to implement:

### Option A: Batch Processing with Delays
```
Process 5 symbols → Wait 60 seconds → Process next 5 symbols
```
- Pros: Simple, guaranteed to work
- Cons: Slower (19 symbols = ~4 batches = ~3 minutes)

### Option B: Adaptive Rate Limiting
```
Monitor response codes → Back off on 429 → Retry after delay
```
- Pros: Faster when possible
- Cons: More complex logic

### Option C: Verify Actual Limits & Optimize
```
Check dashboard → Implement precise throttling
```
- Pros: Optimal performance within your limits
- Cons: Requires knowing exact rate limits

---

## Current Optimization Status

✅ **Completed:**
- Removed artificial sleep delays (was 0.5s per contract)
- Reduced inter-symbol delay (2s → 0.1s)
- Increased contract processing (5 → 20 per strategy)
- Migrated to api.massive.com endpoints

⏳ **Pending:**
- Implement proper rate limit handling
- Add exponential backoff for 429 errors
- Batch processing for large symbol lists

---

## Files Reference

**API Implementation:**
- `python_app/src/data/real_options_fetcher.py` - All Massive.com API calls

**Usage Locations:**
- `python_app/src/pipelines/daily_job.py:164-501` - Main screening loop
- Called for each symbol in universe.csv

**Configuration:**
- `.env` - POLYGON_API_KEY (works with Massive.com)
- `python_app/src/data/universe.csv` - 19 symbols currently

---

## Support Links

- **Massive.com Docs:** https://massive.com/docs
- **Polygon.io Docs:** https://polygon.io/docs (same API, old domain)
- **Rate Limits Info:** https://polygon.io/pricing
- **Dashboard:** https://polygon.io/dashboard

---

**Next Steps:**
1. Check your Massive.com dashboard for exact rate limits
2. Verify Options Advanced tier is active
3. Report back rate limit numbers so we can implement proper throttling
