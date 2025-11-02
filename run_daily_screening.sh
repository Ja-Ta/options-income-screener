#!/bin/bash
#
# Daily Options Screening - Automated Runner
# This script runs the daily options screening with proper logging and error handling
#

# Exit on error
set -e

# Configuration
PROJECT_DIR="/home/oisadm/development/options-income-screener"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/screening_$(date +%Y%m%d).log"
VENV_PATH="$PROJECT_DIR/python_app/venv"
SCRIPT_PATH="$PROJECT_DIR/python_app/src/pipelines/daily_job.py"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to send error notification via Telegram
send_error_notification() {
    local error_msg="$1"
    cd "$PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    python3 -c "
import sys
import os
sys.path.insert(0, 'python_app')
from dotenv import load_dotenv
load_dotenv()
from src.services.telegram_service import TelegramService

telegram = TelegramService()
message = '''❌ **Daily Screening Failed**
━━━━━━━━━━━━━━━━━━━━
📅 $(date '+%Y-%m-%d %H:%M:%S')
⚠️ Error: ${error_msg}

Please check the logs at:
${LOG_FILE}
━━━━━━━━━━━━━━━━━━━━'''
telegram.send_message(message)
" 2>&1 | tee -a "$LOG_FILE"
}

# Start logging
log "================================================"
log "Starting daily options screening"
log "================================================"

# Change to project directory
cd "$PROJECT_DIR" || {
    log "ERROR: Failed to change to project directory"
    exit 1
}

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_PATH/bin/activate" || {
    log "ERROR: Failed to activate virtual environment"
    send_error_notification "Failed to activate virtual environment"
    exit 1
}

# Verify Python version
log "Python version: $(python --version)"
log "Working directory: $(pwd)"

# Run the screening pipeline
log "Running production pipeline..."
log "Command: python -m python_app.src.pipelines.daily_job"

# Execute with error handling
# Note: Pipeline has built-in error notification, but we catch fatal errors too
if python -m python_app.src.pipelines.daily_job 2>&1 | tee -a "$LOG_FILE"; then
    exit_code=0
    log "✅ Pipeline completed successfully"
else
    exit_code=$?
    log "❌ Pipeline failed with exit code: $exit_code"
    send_error_notification "Pipeline exited with code $exit_code"
fi

log "================================================"
log "Daily screening finished (exit code: $exit_code)"
log "================================================"

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "screening_*.log" -mtime +30 -delete 2>/dev/null || true

exit $exit_code
