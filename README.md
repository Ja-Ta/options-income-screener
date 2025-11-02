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
- **Polygon.io**: Market data and option chains
- **Claude AI**: Human-readable pick summaries
- **Telegram Bot**: Daily alerts for top opportunities

## 📊 Key Features

- Daily screening of defined stock universe
- IV Rank and IV Percentile calculations
- Technical trend analysis (SMA, momentum, volatility)
- Risk-adjusted scoring algorithms
- Automated alerts with AI-generated explanations
- Web dashboard with filtering and historical data

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
│       ├── data/       # Polygon API client
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

**Operational Guides**
- **[Management Scripts](MANAGEMENT_SCRIPTS.md)**: Server management and operations
- **[API Documentation](API.md)**: REST API endpoints reference
- **[Scheduling Guide](SCHEDULING.md)**: Automated execution setup
- **[Telegram Setup](TELEGRAM_SETUP.md)**: Bot configuration guide
- **[Monitoring](MONITORING.md)**: Health checks and alerting

## 🧪 Development Status

**Production Ready ✅** - Last Updated: November 2, 2025

**Core System**
- ✅ Real Polygon Options API integration (Options Advanced tier)
- ✅ Unified SQLite database with WAL mode (data/screener.db)
- ✅ Web dashboard at http://157.245.214.224:3000
- ✅ Automated daily screening via cron (10 AM ET, weekdays)
- ✅ Claude AI rationales for top picks
- ✅ Telegram bot alerts with AI insights
- ✅ Real-time options screening with Greeks and IV

**Working Features 🚀**
- ✅ 13-symbol universe (SPY, QQQ, IWM, DIA, AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AMD, JPM)
- ✅ IV Rank and IV Percentile calculations
- ✅ Technical indicators (SMA, momentum, volatility)
- ✅ Risk-adjusted scoring algorithms
- ✅ AI-generated rationales (Claude 3 Haiku)
- ✅ Multi-destination Telegram alerts
- ✅ Comprehensive REST API (15+ endpoints)
- ✅ Database unification (Python ↔ Node.js)
- ✅ Management scripts (start/stop/restart API)
- ✅ Quality monitoring and error handling

**Recent Improvements** (Nov 2, 2025)
- Fixed 4 critical AI rationale quality issues
- Unified database architecture
- Enhanced rationale generation (no truncation, correct symbols)
- Added management scripts for easy server control
- Comprehensive documentation updates

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CLAUDE.md for development guidelines.

## 📧 Contact

GitHub: [@Ja-Ta](https://github.com/Ja-Ta)
