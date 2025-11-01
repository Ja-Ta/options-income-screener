def cc_score(iv_rank, roi_30d, trend_strength, dividend_yield=0.0, below_200sma=False):
    base = 0.40*(iv_rank/100) + 0.30*roi_30d + 0.20*trend_strength + 0.10*dividend_yield
    return base * (0.85 if below_200sma else 1.0)
