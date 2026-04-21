# Gen AI News Agent — AIA Singapore Edition

Automated daily GenAI intelligence digest. See `tasks/prd-gen-ai-news-agent.md` for the full PRD.

## Setup

1. Clone the repo and `cd` into it.
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Place GCP service account JSON at `./video-key.json`.
5. `cp .env.example .env` and fill in `TAVILY_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`.
6. Create `subscribers.json`: `[{"email": "you@example.com", "name": "You", "persona": "all"}]`
7. Manual test: `python -m src.main --days 2`
8. Check inbox + `reports/YYYY-MM-DD_report.md`.
9. Start the scheduler: `python scheduler.py` (daily 08:00 Asia/Singapore).
10. Run tests: `pytest`.
