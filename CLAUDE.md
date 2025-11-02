# CLAUDE.md
### Development Framework, Guidelines & Standards
*(For use with Anthropic Claude Code when collaborating on the Options Income Screener project)*

---

## 🧭 Project Context

This repository implements an **Options Income Screener** designed for **covered call (CC)** and **cash-secured put (CSP)** strategies.  
It helps a **new investor** identify option opportunities that are:
- Liquid and premium-rich  
- Risk-filtered (IV rank, volatility, trend stability)  
- Transparent and easy to interpret  

Claude’s job is to **extend, debug, document, and optimize** code in this repo under consistent standards.

---

## 🧱 Core Stack

| Layer | Technology | Purpose |
|-------|-------------|----------|
| **Backend / ETL** | **Python 3.12 (Ubuntu 24.04 venv)** | Ingestion, screening, scoring, summarization |
| **Data Feed** | Massive.com API (formerly Polygon) | Stock & option chain data |
| **Database** | SQLite (WAL mode) | Persistent store for daily data & picks |
| **Web UI** | Node.js + Express | Read-only dashboard for screened picks |
| **Summaries** | Anthropic Claude API | Generate human-readable rationales |
| **Alerts** | Telegram Bot API | Send daily top picks |
| **Deployment** | DigitalOcean Droplet (Ubuntu 24.04) | Simple production host |

---

## 🧩 Development Framework

Claude Code should adhere to the following **framework workflow**:

1. **Plan before coding**  
   - Restate the requested change or feature.  
   - Summarize assumptions and dependencies.  
   - Confirm any ambiguity before writing code.

2. **Develop incrementally**  
   - Focus on *one module or concern* per iteration.  
   - Maintain idempotent and testable functions.  
   - Include clear docstrings (`"""Explain purpose, inputs, outputs."""`).

3. **Document while coding**  
   - Every new function/class must include:
     - Purpose  
     - Args/returns types  
     - Example usage (if helpful)
   - Update relevant README sections.

4. **Preserve separation of concerns**  
   - **`features/`** = metrics, indicators, computations  
   - **`screeners/`** = logic for filtering candidates  
   - **`scoring/`** = mathematical scoring models  
   - **`services/`** = I/O (Telegram, Claude, scheduling)  
   - **`storage/`** = database interactions  
   - **`pipelines/`** = orchestration of full workflows  

5. **Be cautious with keys and I/O**  
   - Never print or log API keys.  
   - Use `.env` variables (never hardcode).  
   - Use graceful fallbacks and error handling.

---

## ⚙️ Python Environment Enforcement

- All development, testing, and production must run using **Python 3.12**.  
- The interpreter comes preinstalled on Ubuntu 24.04.  
- **No system-wide or conda environments** — only local virtual environments (`python_app/venv`).  
- Every dependency in `requirements.txt` must explicitly support Python 3.12.  
- Verify before development:
  ```bash
  python3.12 --version  # -> Python 3.12.x
  python3.12 -m venv python_app/venv
  source python_app/venv/bin/activate
  pip install -r python_app/requirements.txt

---

## ⚙️ Coding Standards

### Python 3.12

- Style: **PEP 8**, with `black` or `ruff` formatting.
- Type hints: Required on all public functions.
- Logging: Use `logging` module, not `print()`.
- Unit tests: Minimal `pytest` coverage for each logical component.
- Python version compatibility must be 3.12 — avoid features deprecated or removed in 3.13.
- Do not include unused imports or wildcard `*` imports.

**Example pattern**
```python
def compute_iv_rank(today: float, trailing: list[float]) -> float:
    """
    Compute implied volatility rank.
    Args:
        today: current implied volatility value
        trailing: list of trailing daily implied volatilities
    Returns:
        IV rank (0–100)
    """
    ...
```

### Node / JS

- Framework: Express 4 (or Next.js if later upgraded)
- ES Modules syntax only (`import/export`)
- Lint: `eslint:recommended`
- JSON responses only (no HTML templates in API routes)
- Handle all DB errors gracefully

### Database (SQLite)

- WAL mode enabled  
- One logical write per batch (atomic commit)
- Use parameterized queries only (never string concatenation)

### Claude Integration

- Always use structured prompts (see spec Section 15).
- Include minimal fields (`symbol`, `strategy`, `roi_30d`, `ivr`, `score`, `trend`, etc.).
- Keep summaries ≤ 120 words and beginner-friendly.

### Telegram Alerts

- Format must follow the **spec Section 16** pattern exactly.  
- Include emoji/visual clarity; ensure text is plain (no HTML).

---

## 🧠 Quality Assurance

Claude Code should:

- Run linting and tests before pushing changes.
- Never commit `.env`, `.db`, or logs.
- Maintain backward compatibility of database schema.
- Write **clear commit messages**:  
  `feat(screeners): add ROI normalization by DTE`

---

## 🔄 PR / Change Workflow

When Claude Code makes significant changes:

1. **Summarize** the intent at top of the PR (why, what, where).
2. **List affected files**.
3. **Run** local validations:
   ```bash
   pytest -q
   python -m black --check .
   npm run lint
   ```
4. **Verify runtime paths** on a sample SQLite (mock data okay).
5. **Tag** the PR with:
   - `feat:` new functionality  
   - `fix:` bug fix  
   - `chore:` maintenance  
   - `docs:` documentation only

---

## 🧩 Collaboration Guidelines (Claude ↔ Human Developer)

When using Claude Code interactively:

| Task | What Claude Should Do |
|------|-----------------------|
| Add feature | Describe architecture first, then code. |
| Fix bug | Explain root cause, then show patch. |
| Optimize code | Provide benchmark or rationale. |
| Extend schema | Output full new SQL migration. |
| Add API route | Define input/output JSON schemas. |
| Clarify ambiguity | Ask before changing logic. |

---

## 🧪 Testing Standards

| Category | Tool | Example Test |
|-----------|------|--------------|
| Unit | `pytest` | `test_iv_metrics.py` validates IV Rank percentile math |
| Integration | Local SQLite | Mocked Massive/Claude responses |
| API | `supertest` / `curl` | `/api/picks?date=...` returns JSON 200 |
| UI smoke | Browser or curl | Static index renders title properly |

Keep fixtures small and reusable.

---

## 🛡️ Security & Compliance

- No sensitive data in logs or Git history.  
- Validate all external API responses.  
- Catch and sanitize exceptions before user output.  
- Enforce HTTPS (via Nginx + Certbot).  
- Limit Telegram messages per day to prevent spam bans.

---

## 🧰 Recommended Tools for Claude

| Purpose | Tool |
|----------|------|
| Code formatting | `black`, `ruff`, `prettier` |
| Unit testing | `pytest`, `pytest-cov` |
| API testing | `curl`, `httpie`, `supertest` |
| Linting | `eslint`, `flake8` |
| Docs generation | Markdown only |
| Logging | Python `logging`, Node `pino` |

---

## ✅ Completion Definition

A Claude Code task is “complete” when:

1. Code runs without syntax or runtime errors.  
2. Unit tests pass locally.  
3. Lint checks are clean.  
4. The code follows this document’s conventions.  
5. Human-readable rationale or summary is included if the task affects strategy or scoring logic.

---

## 🔒 File & Directory Protections

- **Do not edit:**  
  - `data/screener.db`  
  - `infra/systemd/*.service`  
  - `infra/nginx/*.conf` (unless requested)
- **Editable:** all `python_app/src/` and `node_ui/src/` files  
- **Docs-only updates:** `README.md`, `CLAUDE.md`, `options_income_screener_spec.md`

---

## 💡 Claude Development Example

Example instruction block for future development sessions:

```
User: Claude, please extend the `covered_calls.py` screener to include a check for dividend yield > 1.5%.
Guidelines: Follow CLAUDE.md conventions, update tests, and summarize logic changes at the top.
```

Claude should respond with:
1. Analysis of where to modify the code.  
2. A concise patch proposal.  
3. Updated test(s).  
4. Confirmation of adherence to standards.

---

## 🧩 Future Claude Extensions

Claude may later help add:
- Portfolio risk management
- Backtesting
- Sentiment-driven IV adjustments
- Optional Docker Compose setup for multi-service orchestration

All must follow this CLAUDE.md specification.

---

**End of CLAUDE.md**
