# Monitoring & Error Handling Documentation

## Overview

The Options Income Screener includes a comprehensive monitoring and error handling system that tracks pipeline health, performance metrics, and sends automated alerts when issues arise.

## Components

### 1. MonitoringService (`python_app/src/services/monitoring_service.py`)

**Features:**
- Pipeline execution tracking
- Performance metrics recording
- Failure detection and alerting
- Dead man's switch (alerts if pipeline stops running)
- Health status reporting

**Database Tables:**
- `pipeline_runs` - Execution history with full statistics
- `performance_metrics` - Detailed performance tracking
- `monitoring_alerts` - Alert history

**Key Methods:**
```python
# Start tracking a pipeline run
run_id = monitoring.record_pipeline_start()

# Record completion with statistics
monitoring.record_pipeline_completion(run_id, status='success', stats=stats_dict)

# Record custom metric
monitoring.record_metric(run_id, 'api_latency', 0.25, 'seconds')

# Check if pipeline hasn't run (dead man's switch)
monitoring.check_dead_mans_switch()

# Get current health status
health = monitoring.get_health_status()
```

### 2. Monitoring API Endpoints (`/api/monitoring/`)

Access monitoring data via REST API:

#### GET /api/monitoring/health
Get current system health status with health score (0-100).

**Example:**
```bash
curl http://157.245.214.224:3000/api/monitoring/health
```

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "health_score": 95,
  "last_run": {
    "id": 5,
    "status": "success",
    "total_picks": 12
  },
  "weekly_stats": {
    "total_runs": 5,
    "successful_runs": 5,
    "success_rate": 100
  },
  "recent_alerts_24h": 0
}
```

#### GET /api/monitoring/runs
Get recent pipeline execution history.

**Query Parameters:**
- `limit` - Max results (default: 10)
- `offset` - Pagination offset

**Example:**
```bash
curl "http://157.245.214.224:3000/api/monitoring/runs?limit=5"
```

#### GET /api/monitoring/performance
Get performance metrics summary.

**Query Parameters:**
- `days` - Days to include (default: 7)

**Example:**
```bash
curl "http://157.245.214.224:3000/api/monitoring/performance?days=7"
```

**Response:**
```json
{
  "success": true,
  "period_days": 7,
  "avg_duration_seconds": 18.5,
  "avg_api_calls": 11.2,
  "avg_picks": 12.4
}
```

#### GET /api/monitoring/alerts
Get recent monitoring alerts.

**Query Parameters:**
- `limit` - Max results (default: 20)
- `severity` - Filter by severity ('critical', 'warning', 'info')

**Example:**
```bash
curl "http://157.245.214.224:3000/api/monitoring/alerts?severity=critical"
```

#### POST /api/monitoring/alerts/:id/acknowledge
Acknowledge an alert.

### 3. Dead Man's Switch

**Script:** `check_dead_mans_switch.py`

Checks if the pipeline has run within the threshold (26 hours). If not, sends a critical alert via Telegram.

**Setup:**
Add to crontab to run daily at a different time than the main pipeline:

```bash
crontab -e

# Dead man's switch - runs at 6 PM ET daily (23:00 UTC)
0 23 * * * /home/oisadm/development/options-income-screener/check_dead_mans_switch.py >> /home/oisadm/development/options-income-screener/logs/dead_mans_switch.log 2>&1
```

**Manual Run:**
```bash
cd /home/oisadm/development/options-income-screener
source python_app/venv/bin/activate
python check_dead_mans_switch.py
```

### 4. Automated Alerts

The system automatically sends Telegram alerts for:

#### Consecutive Failures (Critical)
- Triggered after 3 consecutive pipeline failures
- Severity: Critical

#### High Failure Rate (Warning)
- Triggered when > 50% of symbols fail in a run
- Severity: Warning

#### Slow Performance (Info)
- Triggered when pipeline takes > 5 minutes
- Severity: Info

#### Dead Man's Switch (Critical)
- Triggered when no pipeline run in > 26 hours
- Severity: Critical

## Alert Format

Alerts are sent via Telegram with this format:

```
🚨 **Monitoring Alert**
━━━━━━━━━━━━━━━━━━━━
⚠️ 3 Consecutive Pipeline Failures
━━━━━━━━━━━━━━━━━━━━
📅 2025-11-02 14:30:45
🔔 Type: consecutive_failures
📊 Severity: CRITICAL
```

## Error Handling

### Per-Symbol Retry Logic
- 3 retries with 5-second delay
- Failures logged but don't stop pipeline
- Statistics tracked for monitoring

### Fatal Error Handling
- Catches all exceptions in main pipeline
- Sends Telegram notification with error details
- Records error in monitoring database
- Returns proper exit codes

### Database Resilience
- Continues even if Node.js DB sync fails
- Logs all database errors
- Graceful degradation

## Health Score Calculation

Health score (0-100) is calculated based on:

- **Last Run Status** (-30 if failed, -50 if not run)
- **Symbol Success Rate** (-20 if < 50% successful)
- **Weekly Success Rate** (-15 if < 80%)
- **Recent Alerts** (-10 if > 5 in 24 hours)

**Status Levels:**
- `healthy` - Score 80-100
- `degraded` - Score 50-79
- `critical` - Score 0-49

## Monitoring Thresholds (Configurable)

Located in `MonitoringService.__init__()`:

```python
self.max_consecutive_failures = 3  # Alert after N failures
self.max_hours_without_run = 26    # Dead man's switch threshold
self.performance_threshold_seconds = 300  # Slow run threshold (5 min)
```

## Integration with Pipeline

The production pipeline automatically:

1. Records run start when pipeline begins
2. Tracks all statistics during execution
3. Records run completion with full stats
4. Triggers alerts based on thresholds
5. Returns run_id for reference

**Example:**
```python
from src.pipelines.daily_job import run_daily_job

results = run_daily_job()

print(f"Run ID: {results['run_id']}")
print(f"Health Score: {results['stats']['health_score']}")
```

## Troubleshooting

### Check Recent Runs
```bash
sqlite3 data/screener.db "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;"
```

### Check Recent Alerts
```bash
sqlite3 data/screener.db "SELECT * FROM monitoring_alerts ORDER BY created_at DESC LIMIT 10;"
```

### View Performance Metrics
```bash
sqlite3 data/screener.db "SELECT * FROM performance_metrics WHERE run_id = 1;"
```

### Test Monitoring
```python
from src.services.monitoring_service import MonitoringService

monitoring = MonitoringService()
health = monitoring.get_health_status()
print(health)
```

## Best Practices

1. **Check Health Regularly** - Use `/api/monitoring/health` endpoint
2. **Monitor Alerts** - Review `/api/monitoring/alerts` for issues
3. **Track Performance** - Watch for degradation trends
4. **Acknowledge Alerts** - Mark reviewed alerts as acknowledged
5. **Review Logs** - Check `logs/` directory for details
6. **Test Dead Man's Switch** - Verify it works before relying on it

## External Monitoring (Optional)

Consider adding:
- **Uptime monitoring** - Services like UptimeRobot or Pingdom
- **Log aggregation** - Services like Papertrail or Loggly
- **APM** - Application Performance Monitoring tools
- **Custom dashboards** - Grafana or similar visualization

Monitor these endpoints:
- `http://157.245.214.224:3000/api/health` - Overall API health
- `http://157.245.214.224:3000/api/monitoring/health` - Pipeline health

---

**Last Updated:** November 2025
**Version:** 1.0.0
**Status:** Production Ready
