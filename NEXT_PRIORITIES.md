# Next Development Priorities
**Last Updated:** November 2, 2025
**Current Version:** 2.2 (Production Ready)

---

## Executive Summary

The Options Income Screener is now production-ready with all core features operational:
- ✅ 19-symbol universe screening in 31.7 seconds
- ✅ Greek-enhanced scoring with trend analysis
- ✅ Complete AI rationales in Telegram alerts
- ✅ Automated daily execution via cron
- ✅ Comprehensive documentation

This document outlines suggested priorities for the next development session.

---

## Priority 1: Executive Documentation (HIGHEST)

### Status: Started (40% complete)

**Objective:** Create comprehensive executive document for potential clients/investors.

**What's Needed:**
- Executive summary of the application
- Technical foundation section
- System architecture overview
- End-to-end flow diagrams (text-based)
- Screening algorithm explanation (client-friendly)
- Dashboard and alerting engine overview
- Conclusion with future roadmap
- Professional formatting suitable for sharing

**Files to Create:**
- `EXECUTIVE_SUMMARY.md` - Main client-facing document

**Estimated Effort:** 2-3 hours

**Business Value:** High - enables client acquisition and partnership discussions

---

## Priority 2: Earnings Calendar Integration (HIGH)

### Status: Not started (placeholder value = 45 days)

**Objective:** Integrate real earnings dates to avoid selling options before earnings announcements.

**Current State:**
- `earnings_days` hardcoded to 45 (placeholder)
- No actual earnings exclusion logic

**Implementation Plan:**
1. **Data Source Options:**
   - Massive.com API (if available)
   - Yahoo Finance API (free, reliable)
   - Alpha Vantage (free tier available)
   - Financial Modeling Prep API

2. **Code Changes:**
   - Add `get_earnings_date()` method to data fetcher
   - Update `daily_job.py` to fetch earnings for each symbol
   - Implement exclusion window (skip if earnings within 7-10 days)
   - Apply scoring penalty for earnings proximity

3. **Database Schema:**
   - Consider adding `earnings` table for historical tracking
   - Fields: symbol, earnings_date, confirmed, updated_at

**Files to Modify:**
- `python_app/src/data/real_options_fetcher.py`
- `python_app/src/pipelines/daily_job.py`
- `python_app/src/scoring/score_cc.py`
- `python_app/src/scoring/score_csp.py`
- `python_app/src/storage/schema.sql` (optional)

**Testing:**
- Verify earnings dates match official sources
- Test exclusion logic (skip picks near earnings)
- Validate scoring penalties applied correctly

**Estimated Effort:** 4-6 hours

**Business Value:** High - significantly reduces assignment risk during volatile earnings periods

---

## Priority 3: Dividend Data Integration (MEDIUM)

### Status: Not started (placeholder value = 0%)

**Objective:** Integrate real dividend yields to enhance Covered Call scoring.

**Current State:**
- `dividend_yield` hardcoded to 0 (5% weight unused)
- CC scoring missing dividend bonus

**Implementation Plan:**
1. **Data Source Options:**
   - Massive.com API
   - Yahoo Finance API (yfinance library)
   - IEX Cloud API

2. **Code Changes:**
   - Add `get_dividend_yield()` method
   - Update CC scoring to use real dividend data
   - Consider ex-dividend date awareness (advanced)

3. **Scoring Impact:**
   - CC picks with 2%+ dividend yield get 2-5% score boost
   - Particularly valuable for income strategies

**Files to Modify:**
- `python_app/src/data/real_options_fetcher.py`
- `python_app/src/pipelines/daily_job.py`
- `python_app/src/scoring/score_cc.py`

**Estimated Effort:** 2-3 hours

**Business Value:** Medium - enhances CC attractiveness, particularly for dividend-focused investors

---

## Priority 4: Historical Performance Tracking (MEDIUM)

### Status: Not started

**Objective:** Track actual outcomes of picks to validate scoring algorithm.

**Implementation Plan:**
1. **Database Schema:**
   - Add `pick_outcomes` table
   - Fields: pick_id, expiration_result (expired_worthless, assigned, rolled), actual_profit, close_date

2. **Tracking Logic:**
   - Post-expiration job to check pick outcomes
   - Calculate actual vs expected returns
   - Store win rate by strategy/symbol

3. **Analytics:**
   - Win rate dashboard endpoint
   - Average actual ROI vs predicted ROI
   - Best-performing symbols/strategies

4. **ML Future:**
   - Use historical data to train scoring weights
   - Optimize thresholds based on outcomes

**Files to Create:**
- `python_app/src/pipelines/track_outcomes.py`
- `python_app/src/storage/outcomes_schema.sql`
- `node_ui/src/routes/analytics.ts`

**Estimated Effort:** 6-8 hours

**Business Value:** High - validates algorithm effectiveness, enables continuous improvement

---

## Priority 5: Enhanced Telegram Features (LOW-MEDIUM)

### Status: Core features complete

**Objective:** Add interactive features and improved formatting.

**Enhancement Ideas:**
1. **Interactive Buttons:**
   - "View on Dashboard" deep links
   - "Remind me at expiration" button
   - Strategy filter buttons (CC only / CSP only)

2. **Custom Alert Preferences:**
   - User-specific min score thresholds
   - Symbol filters (e.g., "only send AAPL, MSFT alerts")
   - Time preferences (morning vs evening alerts)

3. **Weekly Summary Reports:**
   - Send every Monday with prior week's pick performance
   - Highlight best/worst performers
   - Strategy allocation suggestions

4. **Greeks Display:**
   - Add delta, theta, gamma to alert messages
   - Optional "detailed view" button for full data

**Files to Modify:**
- `python_app/src/services/telegram_service.py`
- `python_app/src/pipelines/daily_job.py`

**Estimated Effort:** 4-6 hours (depending on features selected)

**Business Value:** Medium - improves user experience, adds engagement

---

## Priority 6: Portfolio Management Features (LOW)

### Status: Not started (future enhancement)

**Objective:** Help users manage multiple positions across strategies.

**Features:**
1. **Position Tracking:**
   - User enters opened positions
   - Track aggregate Greeks (portfolio delta, theta)
   - Risk dashboard (concentration by symbol)

2. **Roll Suggestions:**
   - Identify positions near expiration
   - Suggest roll candidates (higher premium, similar risk)
   - Calculate roll efficiency

3. **Assignment Management:**
   - Track CSP assignments → CC opportunities
   - "Wheel strategy" automation

**Estimated Effort:** 10-15 hours (major feature)

**Business Value:** Medium-High (transforms tool into portfolio manager)

**Prerequisites:** Historical tracking, user authentication system

---

## Priority 7: Dashboard Enhancements (LOW)

### Status: Basic dashboard functional

**Enhancement Ideas:**
1. **Advanced Filtering:**
   - Multi-symbol selection
   - Date range picker
   - Custom score/ROI thresholds

2. **Visualizations:**
   - Score distribution histogram
   - IV Rank trends over time
   - Symbol performance heatmap

3. **Comparison Tools:**
   - Side-by-side pick comparison
   - Historical picks for same symbol
   - Strategy performance comparison (CC vs CSP)

4. **Export Features:**
   - CSV export for spreadsheet analysis
   - PDF report generation
   - Email daily digest

**Files to Modify:**
- `node_ui/src/pages/index.tsx`
- `node_ui/src/routes/api.ts`
- `node_ui/src/components/*`

**Estimated Effort:** 6-10 hours (depending on features)

**Business Value:** Medium - improves user experience, adds analytical capabilities

---

## Priority 8: Testing & Quality Assurance (ONGOING)

### Status: Basic testing in place

**Recommendations:**
1. **Unit Test Coverage:**
   - Target 80%+ coverage for scoring algorithms
   - Test edge cases (missing data, extreme values)
   - Mock API responses

2. **Integration Tests:**
   - End-to-end pipeline test with mock data
   - Database integrity tests
   - API endpoint tests

3. **Performance Monitoring:**
   - Set up Sentry or similar error tracking
   - Monitor API latency
   - Track memory usage

4. **Alerting:**
   - Failed screening notifications
   - API quota warnings
   - Database size monitoring

**Estimated Effort:** 4-8 hours (setup + initial tests)

**Business Value:** High - ensures reliability, reduces downtime

---

## Recommended Session Plan

### Next Session (3-4 hours):
1. **Complete Executive Documentation** (1.5-2 hours)
   - Finish `EXECUTIVE_SUMMARY.md`
   - Professional formatting
   - Include text-based architecture diagrams

2. **Start Earnings Calendar Integration** (1.5-2 hours)
   - Research API options
   - Implement data fetching
   - Basic exclusion logic

### Following Sessions:
- **Session 2:** Complete earnings integration + testing
- **Session 3:** Dividend data integration
- **Session 4:** Historical performance tracking (part 1)
- **Session 5:** Historical performance tracking (part 2) + analytics

---

## Technical Debt / Maintenance

### Current State: Excellent
- No critical technical debt
- Code follows standards (CLAUDE.md)
- Documentation comprehensive
- No known bugs

### Periodic Maintenance:
- **Monthly:** Review API usage, check for new Massive.com features
- **Quarterly:** Update dependencies (pip, npm)
- **Annually:** Review scoring weights, retrain if using ML

---

## Risk Assessment

### Low Risk Items:
- Executive documentation (no code changes)
- Dashboard enhancements (UI only)
- Dividend integration (data fetching only)

### Medium Risk Items:
- Earnings calendar (requires new data source)
- Enhanced Telegram features (API changes)

### High Risk Items:
- Historical tracking (schema changes, data migration)
- Portfolio management (major architecture changes)

### Mitigation:
- Test all changes in development environment
- Use feature flags for new functionality
- Maintain rollback capability via Git
- Backup database before schema changes

---

## Success Metrics for Next Features

### Executive Documentation:
- ✓ Document completes without technical jargon
- ✓ Clear value proposition
- ✓ Professional formatting
- ✓ Suitable for non-technical stakeholders

### Earnings Integration:
- ✓ 95%+ accuracy on earnings dates
- ✓ Zero picks within 7 days of earnings
- ✓ Scoring penalties applied correctly
- ✓ No performance degradation

### Dividend Integration:
- ✓ Accurate dividend yields (±0.1%)
- ✓ CC scores increase for dividend stocks
- ✓ Performance impact < 5 seconds

---

## Questions for Next Session

1. **Executive Documentation:**
   - Who is the primary audience? (investors, clients, partners?)
   - Should we include financial projections/performance data?
   - Preferred format (PDF, Markdown, Google Docs)?

2. **Earnings Calendar:**
   - Preferred API provider? (cost, reliability considerations)
   - Exclusion window preference? (7 days, 10 days, custom?)
   - Store earnings history in database?

3. **Future Features:**
   - Any specific user requests or feedback?
   - Priority order different from suggested?

---

**For Next Session:** Focus on **Executive Documentation** first (highest business value, no risk), then begin **Earnings Calendar Integration** if time permits.

**Estimated Total Effort (Priority 1-3):** 8-12 hours across 2-3 sessions

---

**Status:** Ready for next development session
**Prepared by:** Claude Code
**Date:** November 2, 2025
