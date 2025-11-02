# Management Scripts Reference

This document provides complete reference documentation for all management scripts in the Options Income Screener project.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Daily Screening Script](#daily-screening-script)
3. [API Server Management](#api-server-management)
4. [Troubleshooting](#troubleshooting)
5. [Log Files](#log-files)

---

## Overview

The project includes several shell scripts to manage the daily screening pipeline and the Node.js API server:

| Script | Purpose | Location |
|--------|---------|----------|
| `run_daily_screening.sh` | Execute daily options screening pipeline | Project root |
| `start_api.sh` | Start the Node.js API server | Project root |
| `stop_api.sh` | Stop the Node.js API server | Project root |
| `restart_api.sh` | Restart the Node.js API server | Project root |

---

## Daily Screening Script

### `run_daily_screening.sh`

**Purpose:** Runs the complete daily options screening pipeline with proper logging and error handling.

**Location:** `/home/oisadm/development/options-income-screener/run_daily_screening.sh`

### Usage

```bash
# Run manually
./run_daily_screening.sh

# Or via cron (recommended)
# Add to crontab: crontab -e
0 18 * * 1-5 /home/oisadm/development/options-income-screener/run_daily_screening.sh
```

### What It Does

1. ✅ Validates project directory and virtual environment
2. ✅ Activates Python virtual environment
3. ✅ Runs the screening pipeline (`python_app/src/pipelines/daily_job.py`)
4. ✅ Logs all output to daily log files
5. ✅ Sends Telegram notifications on completion or errors
6. ✅ Cleans up old log files (keeps last 30 days)

### Configuration

```bash
PROJECT_DIR="/home/oisadm/development/options-income-screener"
LOG_DIR="$PROJECT_DIR/logs"
VENV_PATH="$PROJECT_DIR/python_app/venv"
SCRIPT_PATH="$PROJECT_DIR/python_app/src/pipelines/daily_job.py"
```

### Log Files

Daily logs are stored in:
```
logs/screening_YYYYMMDD.log
```

Example: `logs/screening_20251102.log`

### Exit Codes

- `0` - Success
- `1` - Failure (environment, pipeline, or execution error)

### Error Handling

- Sends Telegram notification on failure
- Logs all errors to daily log file
- Preserves exit code from pipeline

---

## API Server Management

### `start_api.sh`

**Purpose:** Start the Node.js API server in the background.

**Location:** `/home/oisadm/development/options-income-screener/start_api.sh`

#### Usage

```bash
./start_api.sh
```

#### What It Does

1. ✅ Checks for existing processes on port 3000
2. ✅ Kills any existing server (prevents conflicts)
3. ✅ Starts Node.js server in background (`nohup`)
4. ✅ Runs health check to verify startup
5. ✅ Displays server PID and log location
6. ✅ Shows all API endpoints

#### Output

```
================================================
  Options Income Screener - API Startup
================================================

🔍 Checking for existing processes on port 3000...
✅ Port 3000 is free

🚀 Starting API server...
✅ Server started successfully!
   PID: 123456
   Logs: /tmp/api_server.log
✅ Health check passed

================================================
  Server is running on http://0.0.0.0:3000
  API Docs: http://0.0.0.0:3000/api
  Health:   http://0.0.0.0:3000/api/health
================================================

To view logs: tail -f /tmp/api_server.log
To stop: kill 123456
```

#### Log File

Server output is logged to:
```
/tmp/api_server.log
```

#### Port Configuration

Default port: `3000`

To check if server is running:
```bash
curl http://localhost:3000/api/health
```

---

### `stop_api.sh`

**Purpose:** Cleanly stop the Node.js API server.

**Location:** `/home/oisadm/development/options-income-screener/stop_api.sh`

#### Usage

```bash
./stop_api.sh
```

#### What It Does

1. ✅ Finds process running on port 3000
2. ✅ Attempts graceful shutdown (SIGTERM)
3. ✅ Waits up to 5 seconds for clean exit
4. ✅ Forces shutdown (SIGKILL) if graceful fails
5. ✅ Verifies process is stopped

#### Output

```
================================================
  Options Income Screener - Stop API
================================================

🔍 Looking for server on port 3000...
📍 Found process: PID 123456
⏹️  Attempting graceful shutdown...
   Waiting... (1/5)
✅ Server stopped gracefully
```

#### Shutdown Behavior

**Graceful Shutdown (Preferred):**
- Sends SIGTERM signal
- Allows Node.js to:
  - Close database connections
  - Finish pending requests
  - Clean up resources
- Waits up to 5 seconds

**Forced Shutdown (Fallback):**
- Sends SIGKILL signal
- Immediately terminates process
- Used only if graceful shutdown fails

#### When to Use

- Before deploying code changes
- Before server maintenance
- When server becomes unresponsive
- Before running `restart_api.sh` manually

---

### `restart_api.sh`

**Purpose:** Cleanly restart the Node.js API server.

**Location:** `/home/oisadm/development/options-income-screener/restart_api.sh`

#### Usage

```bash
./restart_api.sh
```

#### What It Does

1. ✅ Calls `stop_api.sh` to cleanly stop server
2. ✅ Waits 2 seconds for complete shutdown
3. ✅ Calls `start_api.sh` to start fresh server
4. ✅ Verifies new server is running

#### Output

Combined output from `stop_api.sh` and `start_api.sh`

#### When to Use

- After code changes to Node.js server
- After database schema changes
- When server needs fresh state
- To clear potential memory leaks

---

## Troubleshooting

### Port 3000 Already in Use

**Problem:** Cannot start API server, port 3000 is busy

**Solution:**
```bash
# Check what's using port 3000
lsof -i:3000

# Stop the API server
./stop_api.sh

# Or manually kill the process
lsof -ti:3000 | xargs kill -9
```

### Server Won't Stop

**Problem:** `stop_api.sh` fails to stop server

**Solution:**
```bash
# Find the process
lsof -i:3000

# Force kill
kill -9 <PID>
```

### Health Check Fails

**Problem:** Server starts but health check fails

**Solution:**
```bash
# Check server logs
tail -f /tmp/api_server.log

# Check database connection
ls -la /home/oisadm/development/options-income-screener/data/screener.db

# Restart the server
./restart_api.sh
```

### Daily Screening Fails

**Problem:** `run_daily_screening.sh` exits with error

**Solution:**
```bash
# Check today's log file
tail -f logs/screening_$(date +%Y%m%d).log

# Verify virtual environment
source python_app/venv/bin/activate
python --version  # Should be 3.12.x

# Check database permissions
ls -la data/screener.db

# Test pipeline manually
cd /home/oisadm/development/options-income-screener
source python_app/venv/bin/activate
python -m python_app.src.pipelines.daily_job
```

### Permission Denied

**Problem:** Scripts won't execute

**Solution:**
```bash
# Make scripts executable
chmod +x run_daily_screening.sh
chmod +x start_api.sh
chmod +x stop_api.sh
chmod +x restart_api.sh
```

### Multiple Node Processes

**Problem:** Multiple node processes running

**Solution:**
```bash
# List all node processes
ps aux | grep node

# Kill all node processes (use with caution!)
pkill -9 node

# Or kill specific PIDs
kill -9 <PID1> <PID2> <PID3>

# Start fresh
./start_api.sh
```

---

## Log Files

### Daily Screening Logs

**Location:** `logs/screening_YYYYMMDD.log`

**Contents:**
- Pipeline start/end timestamps
- Data ingestion progress
- Screening results (picks count)
- AI rationale generation status
- Telegram notification status
- Error messages and stack traces

**View Today's Log:**
```bash
tail -f logs/screening_$(date +%Y%m%d).log
```

**View Specific Date:**
```bash
tail -f logs/screening_20251102.log
```

### API Server Logs

**Location:** `/tmp/api_server.log`

**Contents:**
- Server startup messages
- Database connection status
- HTTP request logs (timestamp, method, endpoint)
- Error messages
- Shutdown messages

**View Logs:**
```bash
tail -f /tmp/api_server.log
```

### Log Rotation

**Daily Screening Logs:**
- New log file created each day
- Old logs auto-deleted after 30 days
- Managed by `run_daily_screening.sh`

**API Server Logs:**
- Single log file at `/tmp/api_server.log`
- Overwrites on each server restart
- Persists until server restart

---

## Quick Reference

### Start Everything
```bash
# Start API server
./start_api.sh
```

### Stop Everything
```bash
# Stop API server
./stop_api.sh
```

### Restart After Code Changes
```bash
# Restart API server
./restart_api.sh
```

### Run Daily Screening Manually
```bash
# Execute screening pipeline
./run_daily_screening.sh
```

### Check Status
```bash
# Check if API is running
curl http://localhost:3000/api/health

# Check server process
lsof -i:3000

# View latest picks
curl http://localhost:3000/api/picks/latest
```

### View Logs
```bash
# Today's screening log
tail -f logs/screening_$(date +%Y%m%d).log

# API server log
tail -f /tmp/api_server.log
```

---

## Database Location

**Unified Database:**
```
/home/oisadm/development/options-income-screener/data/screener.db
```

Both the Python pipeline and Node.js API use this single database.

**Database Mode:** WAL (Write-Ahead Logging) for better concurrent access

**Check Database:**
```bash
# View database info
sqlite3 data/screener.db ".tables"

# Count today's picks
sqlite3 data/screener.db "SELECT COUNT(*) FROM picks WHERE date = date('now');"

# View latest rationales
sqlite3 data/screener.db "SELECT symbol, summary FROM picks p JOIN rationales r ON p.id = r.pick_id ORDER BY r.created_at DESC LIMIT 5;"
```

---

## Environment Variables

### Daily Screening

Set in `.env` file (project root):
```bash
POLYGON_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### API Server

Optional environment variables:
```bash
DB_PATH=/path/to/screener.db  # Defaults to data/screener.db
NODE_ENV=production           # Set by start_api.sh
PORT=3000                     # Default port
```

---

## Cron Setup (Production)

### Schedule Daily Screening

**Recommended:** Run at 6:00 PM ET on weekdays (after market close)

```bash
# Edit crontab
crontab -e

# Add this line (adjust time for your timezone)
0 18 * * 1-5 /home/oisadm/development/options-income-screener/run_daily_screening.sh
```

### Verify Cron

```bash
# List cron jobs
crontab -l

# Check cron service status
sudo service cron status

# View cron logs (Ubuntu)
grep CRON /var/log/syslog
```

---

## Security Notes

### File Permissions

Scripts should be executable only by owner:
```bash
chmod 700 run_daily_screening.sh
chmod 700 start_api.sh
chmod 700 stop_api.sh
chmod 700 restart_api.sh
```

### API Server

- **Default binding:** `0.0.0.0:3000` (accessible from external IPs)
- **Production:** Use Nginx reverse proxy with SSL
- **Firewall:** Configure UFW to restrict port 3000 if needed

### Environment Variables

- Never commit `.env` file to Git
- Keep API keys secure
- Rotate keys periodically

---

## Support

### Check System Status
```bash
# Python version
python3.12 --version

# Node version
node --version

# Virtual environment
source python_app/venv/bin/activate && python --version

# Disk space
df -h

# Memory
free -h
```

### Get Help

1. Check logs first
2. Review error messages
3. Verify environment configuration
4. Test components individually
5. Restart services

---

**Last Updated:** 2025-11-02
**Version:** 1.0
