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

6. **Run tests (mock mode)**
   ```bash
   python test_foundation.py
   ```

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

- **[Technical Specification](options_income_screener_spec.md)**: Complete system design
- **[Development Guide](CLAUDE.md)**: Coding standards and workflows
- **[MVP Roadmap](MVP_ROADMAP.md)**: Implementation checklist

## 🧪 Development Status

**Foundation Complete ✅**
- Mock data generation
- Technical indicators
- IV metrics calculations
- Database schema

**In Progress 🚧**
- Screening algorithms
- Scoring models
- Service integrations
- Web UI

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CLAUDE.md for development guidelines.

## 📧 Contact

GitHub: [@Ja-Ta](https://github.com/Ja-Ta)
