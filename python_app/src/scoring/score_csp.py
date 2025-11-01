def csp_score(iv_rank, roi_30d, margin_of_safety, trend_stability):
    return 0.40*(iv_rank/100) + 0.30*roi_30d + 0.20*margin_of_safety + 0.10*trend_stability
