# Options Income Screener - REST API Documentation

## Base URL
```
http://157.245.214.224:3000/api
```

## Overview

The Options Income Screener provides a RESTful API for accessing daily options picks, statistics, and historical data. All endpoints return JSON responses.

---

## Health & Info

### GET /api/health
Check service health and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "service": "Options Income Screener API",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2025-11-02T01:31:31.068Z"
}
```

### GET /api
Get complete API documentation with all available endpoints.

**Response:**
```json
{
  "name": "Options Income Screener API",
  "version": "1.0.0",
  "endpoints": { ... },
  "queryParameters": { ... }
}
```

---

## Picks Endpoints

### GET /api/picks
Get filtered picks with optional query parameters.

**Query Parameters:**
- `date` (string) - Filter by date (YYYY-MM-DD format)
- `strategy` (string) - Filter by strategy ("CC" or "CSP")
- `minScore` (number) - Minimum score (0-1)
- `minIVR` (number) - Minimum IV Rank (0-100)
- `minROI` (number) - Minimum ROI (decimal)
- `limit` (number) - Max results (default: 100)
- `offset` (number) - Pagination offset

**Example:**
```bash
curl "http://157.245.214.224:3000/api/picks?strategy=CSP&minScore=0.59&limit=5"
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "picks": [
    {
      "id": 13,
      "date": "2025-11-02",
      "symbol": "AAPL",
      "strategy": "CSP",
      "strike": 260,
      "expiry": "2025-12-05",
      "premium": 5.44,
      "stock_price": 270.37,
      "roi_30d": 0.019,
      "annualized_return": 0.228,
      "iv_rank": 23.89,
      "score": 0.596,
      "trend": "neutral",
      "earnings_days": 45
    }
  ]
}
```

### GET /api/picks/latest
Get picks from the most recent date.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/picks/latest"
```

**Response:**
```json
{
  "success": true,
  "date": "2025-11-02",
  "count": 12,
  "picks": [ ... ]
}
```

### GET /api/picks/top
Get top-scoring picks across all dates.

**Query Parameters:**
- `limit` (number) - Max results (default: 10)

**Example:**
```bash
curl "http://157.245.214.224:3000/api/picks/top?limit=5"
```

### GET /api/picks/date/:date
Get all picks for a specific date.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/picks/date/2025-11-02"
```

**Response:**
```json
{
  "success": true,
  "date": "2025-11-02",
  "count": 12,
  "picks": [ ... ]
}
```

### GET /api/picks/:id
Get a single pick by ID.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/picks/13"
```

**Response:**
```json
{
  "success": true,
  "pick": { ... }
}
```

---

## Statistics Endpoints

### GET /api/stats
Get overall statistics across all picks.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/stats"
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "overall": {
      "total_picks": 24,
      "unique_symbols": 3,
      "days_with_picks": 2,
      "avg_score": 0.522,
      "avg_roi": 0.016,
      "avg_ivr": 21.11
    },
    "byStrategy": [
      {
        "strategy": "CC",
        "count": 12,
        "avg_score": 0.498,
        "avg_roi": 0.015,
        "avg_ivr": 19.93
      },
      {
        "strategy": "CSP",
        "count": 12,
        "avg_score": 0.545,
        "avg_roi": 0.017,
        "avg_ivr": 22.29
      }
    ]
  }
}
```

### GET /api/stats/daily/:date
Get daily summary for a specific date.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/stats/daily/2025-11-02"
```

### GET /api/stats/history
Get historical performance data.

**Query Parameters:**
- `days` (number) - Number of days to look back (default: 30)

**Example:**
```bash
curl "http://157.245.214.224:3000/api/stats/history?days=7"
```

### GET /api/stats/dates
Get list of all available dates with pick counts.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/stats/dates"
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "dates": [
    { "date": "2025-11-02", "count": 12 },
    { "date": "2025-11-01", "count": 12 }
  ]
}
```

### GET /api/stats/latest-date
Get the most recent date with picks.

**Example:**
```bash
curl "http://157.245.214.224:3000/api/stats/latest-date"
```

---

## Symbol Endpoints

### GET /api/symbols/search
Search picks by symbol (case-insensitive partial match).

**Query Parameters:**
- `q` (string, required) - Search query (e.g., "AAPL")
- `limit` (number) - Max results (default: 100)

**Example:**
```bash
curl "http://157.245.214.224:3000/api/symbols/search?q=AAPL"
```

**Response:**
```json
{
  "success": true,
  "query": "AAPL",
  "count": 8,
  "picks": [ ... ]
}
```

### GET /api/symbols/:symbol/history
Get historical picks for a specific symbol.

**Query Parameters:**
- `days` (number) - Number of days to look back (default: 30)
- `strategy` (string) - Filter by strategy ("CC" or "CSP")

**Example:**
```bash
curl "http://157.245.214.224:3000/api/symbols/AAPL/history"
```

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "count": 8,
  "history": [ ... ]
}
```

---

## Data Schema

### Pick Object
Each pick contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Unique pick identifier |
| `date` | string | Pick date (YYYY-MM-DD) |
| `asof` | string | Data as-of date |
| `symbol` | string | Stock symbol |
| `strategy` | string | "CC" (Covered Call) or "CSP" (Cash-Secured Put) |
| `strike` | number | Option strike price |
| `expiry` | string | Option expiration date (YYYY-MM-DD) |
| `premium` | number | Option premium (price) |
| `stock_price` | number | Current stock price |
| `roi_30d` | number | 30-day return on investment (decimal) |
| `annualized_return` | number | Annualized return (decimal) |
| `iv_rank` | number | Implied Volatility Rank (0-100) |
| `score` | number | Composite score (0-1) |
| `rationale` | string\|null | AI-generated rationale (if available) |
| `trend` | string | Price trend ("uptrend", "neutral", "downtrend") |
| `earnings_days` | number | Days until earnings (estimated) |
| `created_at` | string | Timestamp when pick was created |

---

## Error Responses

All endpoints return error responses in this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Internal server error

---

## Rate Limiting

Currently no rate limiting is enforced. Please use the API responsibly.

---

## CORS

CORS is enabled for all origins. The API can be accessed from web browsers.

---

## Examples

### Get today's top CSP picks with score > 0.59
```bash
curl "http://157.245.214.224:3000/api/picks?strategy=CSP&minScore=0.59&limit=5"
```

### Get all AAPL picks from the last 30 days
```bash
curl "http://157.245.214.224:3000/api/symbols/AAPL/history?days=30"
```

### Get picks for a specific date
```bash
curl "http://157.245.214.224:3000/api/picks/date/2025-11-02"
```

### Get overall statistics
```bash
curl "http://157.245.214.224:3000/api/stats"
```

---

## Support

For issues or questions:
- Dashboard: http://157.245.214.224:3000
- GitHub: Check project repository
- Documentation: See README.md and PROJECT_STATUS.md

---

**Last Updated:** November 2025
**API Version:** 1.0.0
