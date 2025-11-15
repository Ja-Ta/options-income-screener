# Options Income Screener

AI-powered options screener for covered calls and cash-secured puts strategies.

## 🎯 Purpose

This screener helps identify high-quality options trading opportunities for income generation through:
- **Covered Calls (CC)**: Selling calls against owned stock positions
- **Cash-Secured Puts (CSP)**: Selling puts backed by cash reserves

## 🛠 Tech Stack

- **Python 3.12**: Data ingestion, screening, and scoring algorithms
- **SQLite**: Persistent storage with WAL mode for concurrent access
- **Node.js/Express**: Web UI and REST API
- **Massive.com** (formerly Polygon.io): Market data and option chains
- **Claude AI**: Human-readable pick summaries
- **Telegram Bot**: Daily alerts for top opportunities

## 📊 Key Features

- Daily screening of defined stock universe (106 symbols)
- IV Rank and IV Percentile calculations
- Technical trend analysis (SMA, momentum, volatility)
- **Earnings calendar integration** with color-coded proximity warnings
- **Sentiment analysis** (contrarian signals, P/C ratio, Chaikin Money Flow)
- **Real dividend data** integration for accurate income projections
- Risk-adjusted scoring algorithms with Greek analysis
- Automated alerts with AI-generated explanations
- **Tabbed web dashboard** with sortable columns and sentiment filters
- Production-ready deployment with custom domain and SSL

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ja-Ta/options-income-screener.git
   cd options-income-screener
   ```

2. **Set up Python environment**
   ```bash
   python3.12 -m venv python_app/venv
   source python_app/venv/bin/activate
   pip install -r python_app/requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   cd node_ui && npm install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Initialize database**
   ```bash
   sqlite3 data/screener.db < python_app/src/storage/schema.sql
   ```

6. **Start the API server**
   ```bash
   ./start_api.sh
   ```

7. **Run daily screening**
   ```bash
   ./run_daily_screening.sh
   ```

See **[Management Scripts](MANAGEMENT_SCRIPTS.md)** for detailed operational guides.

## 📁 Project Structure

```
├── python_app/          # Python backend
│   └── src/
│       ├── data/       # Massive.com API client (market data)
│       ├── features/   # Technical & IV metrics
│       ├── screeners/  # CC & CSP screening logic
│       ├── scoring/    # Scoring algorithms
│       └── pipelines/  # Daily job orchestration
├── node_ui/            # Express web server
├── data/               # SQLite database & logs
└── infra/              # Deployment configs
```

## 📖 Documentation

**Core Documentation**
- **[Technical Specification](options_income_screener_spec.md)**: Complete system design
- **[Development Guide](CLAUDE.md)**: Coding standards and workflows
- **[MVP Roadmap](MVP_ROADMAP.md)**: Implementation checklist
- **[Project Status](PROJECT_STATUS.md)**: Current system status and metrics
- **[Executive Summary](EXECUTIVE_SUMMARY.md)**: High-level business overview

**Operational Guides**
- **[Management Scripts](MANAGEMENT_SCRIPTS.md)**: Server management and operations
- **[API Documentation](API.md)**: REST API endpoints reference
- **[Dashboard Guide](DASHBOARD_v2.8.md)**: Dashboard UI features and usage
- **[Telegram Guide](TELEGRAM_v2.8.md)**: Alert formats and configuration
- **[Monitoring](MONITORING.md)**: Health checks and alerting

**Development Sessions**
- **[v2.9 Session](SESSION_v2.9.md)**: Tabbed interface and sortable columns
- **[v2.7-v2.8 Session](SESSION_v2.7-v2.8.md)**: Sentiment analysis integration

## 🧪 Development Status

**Production Ready ✅** - Last Updated: November 15, 2025

**Core System**
- ✅ Real Massive.com Options API integration (Options Advanced tier, formerly Polygon.io)
- ✅ Unified SQLite database with WAL mode (data/screener.db)
- ✅ Web dashboard at https://oiscreener.com (custom domain with SSL)
- ✅ Automated daily screening via cron (10 AM ET, weekdays)
- ✅ Claude AI rationales for top picks
- ✅ Telegram bot alerts with AI insights
- ✅ Real-time options screening with Greeks and IV
- ✅ Sentiment analysis with contrarian signals
- ✅ Real dividend data integration

**Working Features 🚀**
- ✅ 106-symbol universe loaded from CSV (expanded from 19 to 106 symbols)
- ✅ IV Rank and IV Percentile calculations
- ✅ Technical indicators (SMA, momentum, volatility)
- ✅ Sentiment metrics (P/C Ratio, CMF-20, contrarian signals)
- ✅ Earnings calendar with color-coded proximity warnings
- ✅ Real dividend yield data from Massive.com API
- ✅ Risk-adjusted scoring algorithms
- ✅ AI-generated rationales (Claude 3 Haiku)
- ✅ Multi-destination Telegram alerts
- ✅ Tabbed dashboard (CC/CSP separation)
- ✅ Sortable columns with visual indicators
- ✅ Sentiment filtering and badges
- ✅ Comprehensive REST API (15+ endpoints)
- ✅ Database unification (Python ↔ Node.js)
- ✅ Management scripts (start/stop/restart API)
- ✅ Quality monitoring and error handling
- ✅ Production deployment with nginx + Let's Encrypt

**Recent Improvements** (Nov 2 - Nov 15, 2025)

*Domain & SSL Setup (v2.10)* - Nov 15, 2025
- 🌐 Custom domain configured: https://oiscreener.com
- 🔒 SSL certificate from Let's Encrypt (auto-renews every 90 days)
- ✅ nginx reverse proxy with automatic HTTP→HTTPS redirect
- ✅ Updated all Telegram alerts and documentation to use new domain
- ✅ Production-ready secure deployment

*Dashboard Enhancements (v2.9)* - Nov 14, 2025
- 📊 Tabbed interface: Separate tabs for Covered Calls (CC) and Cash-Secured Puts (CSP)
- 🔄 Sortable columns: All 14 table columns now sortable with visual indicators (▲▼)
- ✨ Enhanced UX: Green arrows show sort direction, tabs have active states
- 🔧 API updates: `/api/picks/latest` supports strategy filtering

*Sentiment Visualization (v2.8)* - Nov 13, 2025
- 🎯 Sentiment badges in dashboard (🟢 Long, 🔴 Short, ⚪ Neutral)
- 💡 Interactive tooltips with detailed sentiment explanations
- 🔍 Sentiment filtering: Filter picks by contrarian signal type
- 📊 Visual P/C Ratio and CMF indicators with color coding

*Sentiment Analysis Integration (v2.7)* - Nov 12, 2025
- 🎯 Contrarian signal generation (long/short/neutral)
- 📊 Put/Call ratio analysis with crowd sentiment interpretation
- 💰 Chaikin Money Flow (CMF-20) for smart money tracking
- ✅ Full integration in screening pipeline and Telegram alerts
- 📖 Comprehensive sentiment analysis documentation

*Earnings Display Enhancement (v2.6)* - Nov 8, 2025
- 📅 Earnings date column in dashboard with days-until display
- 🚨 Color-coded proximity warnings:
  - 🔴 Red (<7 days) - Severe risk
  - 🟠 Orange (7-14 days) - Strong risk
  - 🟡 Yellow (14-21 days) - Moderate risk
  - 🟢 Green (21-30 days) - Light risk
  - ✅ Safe (>30 days) - Low risk
- ✅ Earnings warnings in Telegram alerts

*Dividend Integration (v2.5)* - Nov 5, 2025
- 💵 Real dividend data from Massive.com API
- 📊 Dividend yield column in dashboard
- ✅ Accurate income projections for covered calls
- ✅ Integrated into scoring algorithm

*Earlier Updates (v2.1-v2.4)*
- 🚀 Migrated to Massive.com API (formerly Polygon.io)
- 🚀 Expanded universe to 106 symbols (from 19)
- 🚀 83% faster screening performance
- ✅ Unified database architecture
- ✅ Enhanced Telegram alert formatting
- ✅ Comprehensive API documentation
- ✅ Management scripts for operations

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CLAUDE.md for development guidelines.

## 📧 Contact

GitHub: [@Ja-Ta](https://github.com/Ja-Ta)
