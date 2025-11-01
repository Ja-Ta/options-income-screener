"""
Constants and configuration parameters for the Options Income Screener.

Follows CLAUDE.md conventions with Python 3.12 compatibility.
All thresholds and parameters are defined here for easy tuning.
"""

# ===== Price & Liquidity Filters =====
MIN_PRICE = 10.0  # Minimum stock price for screening
MIN_OPTION_OI = 500  # Minimum open interest for option contracts
MIN_OPTION_VOLUME = 50  # Minimum daily volume for option contracts
MAX_SPREAD_PCT = 0.10  # Maximum bid-ask spread as % of mid price (10%)

# ===== Option Contract Parameters =====
# Covered Calls
CC_DELTA_RANGE = (0.25, 0.35)  # Call delta range for CC strategy
CC_DTE_RANGE = (30, 45)  # Days to expiration range for CC

# Cash-Secured Puts
CSP_DELTA_RANGE = (0.25, 0.30)  # Put delta range for CSP strategy
CSP_DTE_RANGE = (30, 45)  # Days to expiration range for CSP

# ===== Volatility & IV Filters =====
CC_MIN_IVR = 40  # Minimum IV Rank for covered calls (40%)
CSP_MIN_IVR = 50  # Minimum IV Rank for cash-secured puts (50%)
MAX_HV_60 = 0.50  # Maximum 60-day historical volatility (50%)

# ===== Earnings & Events =====
EARNINGS_EXCLUSION_DAYS = 10  # Exclude if earnings within +/- N days

# ===== Performance Targets =====
CC_ANNUALIZED_TARGET = 0.15  # Target annualized ROI for CC (15%)
CSP_ANNUALIZED_TARGET = 0.12  # Target annualized ROI for CSP (12%)

# ===== Alerts & Display =====
TOP_N_ALERTS_PER_STRATEGY = 5  # Max alerts per strategy per day
SCORE_THRESHOLD = 0.50  # Minimum score to qualify for alerts

# ===== Trend Indicators =====
TREND_SMA_PERIODS = {
    'fast': 20,
    'medium': 50,
    'slow': 200
}

# ===== Scoring Weights =====
# Covered Calls scoring weights
CC_SCORING_WEIGHTS = {
    'iv_rank': 0.40,
    'roi_30d': 0.30,
    'trend_strength': 0.20,
    'dividend_yield': 0.10
}

# Cash-Secured Puts scoring weights
CSP_SCORING_WEIGHTS = {
    'iv_rank': 0.40,
    'roi_30d': 0.30,
    'margin_of_safety': 0.20,
    'trend_stability': 0.10
}

# ===== Penalties & Adjustments =====
BELOW_SMA200_PENALTY = 0.85  # Score multiplier when below 200 SMA

# ===== Data Processing =====
BATCH_SIZE = 50  # Symbols per batch for API calls
MAX_RETRIES = 3  # Max retries for failed API calls
RETRY_DELAY = 1.0  # Initial delay in seconds for retries

# ===== Mock Data Mode =====
import os
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() == "true"  # Load from environment
MOCK_UNIVERSE_SIZE = 5  # Number of symbols for mock testing