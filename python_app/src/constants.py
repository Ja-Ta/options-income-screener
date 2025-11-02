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

# ===== Greeks Thresholds =====
# Theta (time decay per day)
THETA_OPTIMAL_RANGE = (0.05, 0.15)  # Optimal absolute theta for income (daily decay)
THETA_MIN = 0.03  # Minimum absolute theta to consider
THETA_MAX = 0.25  # Maximum absolute theta (too risky above this)

# Gamma (delta stability)
GAMMA_LOW_THRESHOLD = 0.001  # Low gamma = stable delta (preferred)
GAMMA_HIGH_THRESHOLD = 0.003  # High gamma = unstable delta (penalty)

# Vega (IV sensitivity)
VEGA_HIGH_THRESHOLD = 0.20  # High vega for high IV environments
VEGA_LOW_THRESHOLD = 0.08  # Low vega for low IV environments

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

# Trend strength thresholds (-1 to 1 scale)
TREND_STRENGTH_STRONG = 0.5       # > 0.5 = strong uptrend
TREND_STRENGTH_WEAK = -0.5        # < -0.5 = strong downtrend
# Between -0.5 and 0.5 = neutral/mixed

# Trend stability thresholds (0 to 1 scale)
TREND_STABILITY_HIGH = 0.7        # > 0.7 = very stable trend
TREND_STABILITY_LOW = 0.4         # < 0.4 = volatile/unstable
# Between 0.4 and 0.7 = moderate stability

# RSI thresholds (0 to 100 scale)
RSI_OVERBOUGHT = 70               # RSI > 70 = overbought
RSI_OVERSOLD = 30                 # RSI < 30 = oversold
RSI_NEUTRAL = 50                  # RSI = 50 = neutral momentum

# Historical data requirements
HISTORICAL_BARS_REQUIRED = 200    # Minimum bars for SMA200 calculation
HISTORICAL_DAYS_TO_FETCH = 300    # Calendar days to fetch (ensures 200+ trading days, accounting for weekends/holidays)

# ===== Scoring Weights =====
# Covered Calls scoring weights (must sum to 1.0)
CC_SCORING_WEIGHTS = {
    'iv_rank': 0.25,          # IV environment importance
    'roi_30d': 0.30,          # Return on investment
    'trend_strength': 0.15,   # Trend direction
    'dividend_yield': 0.05,   # Dividend bonus
    'theta': 0.10,            # Time decay value
    'gamma': 0.05,            # Delta stability
    'vega': 0.10              # IV sensitivity match
}

# Cash-Secured Puts scoring weights (must sum to 1.0)
CSP_SCORING_WEIGHTS = {
    'iv_rank': 0.25,          # IV environment importance
    'roi_30d': 0.30,          # Return on investment
    'margin_of_safety': 0.15, # Downside protection
    'trend_stability': 0.05,  # Trend consistency
    'theta': 0.10,            # Time decay value
    'gamma': 0.05,            # Delta stability
    'vega': 0.10              # IV sensitivity match
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