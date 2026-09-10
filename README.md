# VTU Internship Watcher

A Python-based watcher for internship listings on the VTU Internyet portal. It renders the portal, evaluates each opportunity against a configurable technical-skill profile, stores the latest record in SQLite, and sends Telegram alerts for relevant new listings and meaningful listing updates.

## Current capabilities

- Scrapes the React-based VTU Internyet portal with Playwright/Chromium, including lazy-loaded listing cards and individual listing details.
- Parses title, company, description, skills, category, location, mode, internship type, fee/stipend, duration, vacancies, application status, deadline, and URL.
- Scores technical relevance from title, listed skills, category, and description using weighted keywords in `config/skills.yaml`.
- Applies configurable hard filters: technical match must meet the minimum score, and paid internships above the maximum fee are ignored.
- Ranks remaining listings as `VERY_HIGH`, `HIGH`, `MEDIUM`, or `LOW` based on match score, stipend/free/paid type, and Remote/Hybrid/Onsite mode.
- Saves a current snapshot of every listing in SQLite, keyed by the portal ID.
- Detects changes to vacancy, application status, deadline, fee, mode, stipend, type, location, and duration on later checks.
- Sends one Telegram notification for a qualifying new listing and deduplicated Telegram update notifications for each distinct change event.
- Supports one-off checks, continuous polling, dry runs, stored-listing display, database statistics, and Telegram connection testing.

## How it works

```text
VTU Internyet portal
        |
        v
Playwright-rendered listings and detail pages
        |
        v
Parser -> weighted skill matcher -> filters and priority scorer
        |
        +--> New listing: save snapshot and notify when qualifying
        |
        +--> Existing listing: compare snapshot, update database,
             and notify once for each meaningful change
```

## Tech stack

- Python 3
- Playwright and Chromium for browser rendering
- Beautiful Soup and Requests for parsing/network support
- SQLite for persistent storage and notification deduplication
- PyYAML and python-dotenv for configuration
- Telegram Bot API for alerts
- Pytest for tests

## Project structure

```text
VTU-Internship-Watcher/
|-- config/
|   |-- config.yaml          # Filters and priority-score settings
|   `-- skills.yaml          # Skill categories, weights, and keywords
|-- data/
|   `-- internships.db       # Created/updated locally at runtime
|-- scripts/
|   `-- test_portal.py       # Portal and matching diagnostic
|-- src/
|   |-- collector/           # Playwright scraper and browser helper
|   |-- parser/              # Listing and detail parsers
|   |-- matching/            # Skill profile, matching, and priority scoring
|   |-- database/            # SQLite models and repository
|   |-- monitoring/          # Monitoring and change-detection workflow
|   |-- notifications/       # Telegram notifier and SMTP email utility
|   `-- utils/               # Logging and normalization helpers
|-- tests/                   # Unit tests, including change detection
|-- .env.example
|-- requirements.txt
`-- run.py                   # CLI entry point
```

## Setup

1. Create and activate a Python virtual environment (recommended).

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Copy `.env.example` to `.env` and set your Telegram credentials:

   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_CHAT_ID=987654321
   ```

   Create a bot through `@BotFather`. Start a chat with that bot before testing delivery, then obtain your chat ID from a Telegram ID bot.

4. Optionally set `VTU_PORTAL_URL` in `.env` to use a different portal base URL. It defaults to `https://vtu.internyet.in`.

## Usage

Run a single monitoring cycle (the default):

```bash
python run.py
# or
python run.py --once
```

Run continuously, checking every 30 minutes:

```bash
python run.py --loop --interval 30
```

Preview a cycle without writing to SQLite or sending Telegram messages:

```bash
python run.py --dry-run
```

Review local data:

```bash
python run.py --stats
python run.py --list
```

Verify Telegram credentials and delivery:

```bash
python run.py --test-telegram
```

Run the portal diagnostic:

```bash
python scripts/test_portal.py
```

## Matching and priority rules

The skill profile in `config/skills.yaml` currently covers AI/ML, Python, computer vision, NLP, data science, full-stack development, frontend development, analytics, software engineering, SQL, and Java. Adjust its keywords and category weights to reflect your own target roles.

`config/config.yaml` currently sets:

- Minimum technical match: `50%`
- Maximum paid internship fee: `Rs. 2,000`
- Priority adjustments: stipend, free/paid status, and internship mode

Listings below the match threshold or paid listings above the fee cap receive `IGNORE`. The remaining priority reflects the technical match plus preference rules; stipend and remote opportunities receive the strongest preference.

## Notifications and data behavior

Telegram alerts are sent for new `VERY_HIGH`, `HIGH`, and `MEDIUM` listings. When a tracked listing changes, the watcher compares the current portal snapshot with the stored one and can send a separate, deduplicated update alert. Failed sends are not marked as delivered, so a later cycle can retry them.

An SMTP email notifier utility exists in `src/notifications/email.py`, but email summaries are not yet invoked by the monitoring workflow. Telegram is the active notification channel.

The SQLite database is stored at `data/internships.db`; logs are written to `logs/watcher.log`. Both are local runtime data and should remain untracked.

## Testing

```bash
pytest -v tests/
```

The suite covers scraping behavior, parsing, matching, priority scoring, database operations, and change detection.

## Notes

- The live portal structure can change. If no listings are extracted, check `logs/watcher.log` and run `python scripts/test_portal.py` to diagnose the rendered page and parser behavior.
- Playwright is required for normal live scraping because the portal renders its content client-side.
- Mock listing data is available only when explicitly enabled in the scraper for development/testing; it is not used as the default live-scraping fallback.
