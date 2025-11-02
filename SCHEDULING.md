# Automated Scheduling Documentation

## Overview

The Options Income Screener runs automatically every weekday at **10:00 AM Eastern Time** using a cron job. The system uses a production-ready pipeline (`ProductionPipeline`) with comprehensive error handling, retry logic, and automated alerts. This document explains how the scheduling works and how to manage it.

## Schedule

### Daily Options Screening
- **Time:** 10:00 AM Eastern Time (15:00 UTC)
- **Days:** Monday through Friday (weekdays only)
- **No execution on:** Weekends and market holidays

### Dead Man's Switch (Health Check)
- **Time:** 6:00 PM Eastern Time (23:00 UTC)
- **Days:** Every day (including weekends)
- **Purpose:** Verify pipeline is running, alert if stale

## Components

### 1. Cron Job

The cron jobs are configured in the user's crontab:

```cron
# Daily options screening - runs at 10 AM ET (3 PM UTC) on weekdays
0 15 * * 1-5 /home/oisadm/development/options-income-screener/run_daily_screening.sh

# Dead man's switch - checks pipeline health daily at 6 PM ET (11 PM UTC)
0 23 * * * /home/oisadm/development/options-income-screener/python_app/venv/bin/python /home/oisadm/development/options-income-screener/check_dead_mans_switch.py >> /home/oisadm/development/options-income-screener/logs/dead_mans_switch.log 2>&1
```

**Cron schedule breakdown (Daily Screening):**
- `0` - Minute (0 = top of the hour)
- `15` - Hour (15 = 3 PM UTC / 10 AM EST)
- `*` - Day of month (any day)
- `*` - Month (any month)
- `1-5` - Day of week (Monday-Friday)

**Cron schedule breakdown (Dead Man's Switch):**
- `0` - Minute (0 = top of the hour)
- `23` - Hour (23 = 11 PM UTC / 6 PM EST)
- `*` - Day of month (any day)
- `*` - Month (any month)
- `*` - Day of week (every day)

### 2. Wrapper Script

**Location:** `/home/oisadm/development/options-income-screener/run_daily_screening.sh`

The wrapper script handles:
- Environment setup
- Virtual environment activation
- Production pipeline execution (`src.pipelines.daily_job`)
- Comprehensive logging
- Error notifications via Telegram (double failsafe)
- Log rotation (keeps last 30 days)

**Pipeline Features:**
- 3 retries with 5-second delay for API failures
- Comprehensive error handling per symbol
- Database writes to both Python and Node.js DBs
- Claude AI rationale generation (top 5 picks)
- Telegram alerts with AI insights
- Detailed statistics and duration tracking

### 3. Logs

**Location:** `/home/oisadm/development/options-income-screener/logs/`

Log files are named: `screening_YYYYMMDD.log`

**Example:** `screening_20251102.log`

Logs include:
- Execution timestamps
- Script output
- Error messages
- Exit codes

## Management Commands

### View Current Cron Jobs

```bash
crontab -l
```

### Edit Cron Jobs

```bash
crontab -e
```

### Remove Cron Job

```bash
crontab -r  # WARNING: Removes ALL cron jobs
```

Or edit with `crontab -e` and delete the specific line.

### Manually Run Screening

To run the screening manually (outside of the cron schedule):

```bash
/home/oisadm/development/options-income-screener/run_daily_screening.sh
```

Or run the Python script directly:

```bash
cd /home/oisadm/development/options-income-screener
source python_app/venv/bin/activate
cd python_app
python -m src.pipelines.daily_job
```

Or use the wrapper script:
```bash
/home/oisadm/development/options-income-screener/run_daily_screening.sh
```

### View Recent Logs

```bash
# View today's log
tail -f /home/oisadm/development/options-income-screener/logs/screening_$(date +%Y%m%d).log

# View all recent logs
ls -lt /home/oisadm/development/options-income-screener/logs/
```

### Check Cron Service Status

```bash
systemctl status cron
```

## Error Handling

### Automatic Error Notifications

If the screening fails, the system automatically:
1. Logs the error to the daily log file
2. Sends a Telegram alert with error details
3. Includes the log file path for debugging

### Common Issues

#### Cron job not running

1. Check if cron service is active:
```bash
systemctl is-active cron
```

2. Check cron logs:
```bash
grep CRON /var/log/syslog | tail -20
```

#### Script fails to execute

1. Check script permissions:
```bash
ls -l /home/oisadm/development/options-income-screener/run_daily_screening.sh
```
Should show: `-rwxr-xr-x` (executable)

2. Check the log file for error messages

#### Virtual environment not found

Ensure the virtual environment exists:
```bash
ls -d /home/oisadm/development/options-income-screener/python_app/venv
```

#### API Rate Limiting

If you hit Polygon API rate limits:
- Review the symbols list in `real_polygon_screening.py`
- Adjust sleep times between API calls
- Consider upgrading your Polygon API plan

## Timezone Considerations

- **Server timezone:** UTC
- **Market timezone:** Eastern Time (ET)
- **Cron runs at:** 15:00 UTC
- **Market time:** 10:00 AM ET (30 minutes after market open)

**Note:** During Daylight Saving Time changes, verify the cron time still aligns with market hours.

## Modifying the Schedule

To change the execution time, edit the cron job:

```bash
crontab -e
```

### Example: Run at 11 AM ET instead

```cron
# 11 AM ET = 4 PM UTC
0 16 * * 1-5 /home/oisadm/development/options-income-screener/run_daily_screening.sh
```

### Example: Run on specific days

```cron
# Run only on Monday, Wednesday, Friday
0 15 * * 1,3,5 /home/oisadm/development/options-income-screener/run_daily_screening.sh
```

## Monitoring

### Check if screening ran today

```bash
ls -l /home/oisadm/development/options-income-screener/logs/screening_$(date +%Y%m%d).log
```

### View execution summary

```bash
grep "completed successfully\|failed" /home/oisadm/development/options-income-screener/logs/screening_*.log
```

### Check database for today's picks

```bash
sqlite3 /home/oisadm/development/options-income-screener/data/screener.db \
  "SELECT COUNT(*) as picks FROM picks WHERE date = DATE('now');"
```

## Troubleshooting

### Force a test run

```bash
# Run the wrapper script to test everything
/home/oisadm/development/options-income-screener/run_daily_screening.sh

# Check the log
tail -100 /home/oisadm/development/options-income-screener/logs/screening_$(date +%Y%m%d).log
```

### Verify environment

```bash
# Check Python version in venv
source /home/oisadm/development/options-income-screener/python_app/venv/bin/activate
python --version  # Should be Python 3.12.x
```

### Test Telegram notifications

The wrapper script will send Telegram alerts on failures. To test:

```bash
python python_app/test_telegram_multi.py
```

## Log Retention

- Logs are automatically cleaned up after **30 days**
- Each day creates a new log file
- To change retention period, edit `run_daily_screening.sh`:

```bash
# Find this line and change +30 to desired days
find "$LOG_DIR" -name "screening_*.log" -mtime +30 -delete
```

## Security Considerations

- The cron job runs as the `oisadm` user
- API keys are stored in `.env` file (not in version control)
- Logs may contain sensitive data - protect access
- Scripts should never be world-writable

## Next Steps

After setup:
1. Wait for the first automated run (next weekday at 10 AM ET)
2. Check the log file after execution
3. Verify picks were saved to database
4. Confirm Telegram alerts were received

---

**Last Updated:** November 2025
**Setup Completed:** Yes ✅
**Status:** Active and running