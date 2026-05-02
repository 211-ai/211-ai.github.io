# 211-AI

**211-info + AI** — a comprehensive scraper and data pipeline for [211info.org](https://www.211info.org), designed to power AI agents that help individuals navigate social services in Oregon and SW Washington.

---

## Overview

[211info.org](https://www.211info.org) is a resource directory for more than **7,000** non-profit, government, and faith-based health and social-service programmes across Oregon and SW Washington.  This project scrapes, normalises, and stores all of that data so that AI liaison agents can:

* Answer natural-language questions about available services
* Match individuals to programmes based on their situation
* Guide people through eligibility, hours, and contact details
* Act as a personal advocate between citizens and public services

---

## Scraped data categories

| Category | Examples |
|---|---|
| Crisis Hotlines | Suicide prevention, domestic violence, poison control |
| Housing & Shelter | Emergency shelters, transitional housing, rent assistance |
| Utility Assistance | Energy, water, phone bill help |
| Child Care & Parenting | Daycare subsidies, parenting classes |
| Food | Food pantries, SNAP, school meals |
| Basic Needs | Clothing, hygiene, household goods |
| Foster Families | Foster recruitment, support services |
| Health Care | Free clinics, dental, vision, mental health |
| Mental & Behavioral Health | Counselling, substance abuse, peer support |
| Transportation | Medical transport, bus passes |
| Legal & Public Safety | Legal aid, victim services, immigration |
| Employment | Job training, resume help, unemployment |
| Education | Adult education, literacy, ESL |
| Financial Wellness | Credit counselling, tax prep, benefits |
| Diverse Populations | LGBTQ+, seniors, veterans, immigrants |
| Youth Services | After-school, mentoring, runaway services |
| Disaster Services | Emergency food, shelter, rebuilding |

---

## Project structure

```
211-AI/
├── scraper/
│   ├── __init__.py          # package exports
│   ├── config.py            # all tuneable constants & Config class
│   ├── utils.py             # logging, rate-limit, URL & text helpers
│   ├── storage.py           # JSON / JSONL / CSV / HTML I/O
│   ├── static_scraper.py    # requests + BeautifulSoup for static pages
│   ├── browser_scraper.py   # Playwright for JS-rendered search pages
│   ├── processor.py         # deduplicate, normalise, export
│   └── main.py              # CLI entry point
├── data/
│   ├── raw/                 # raw scraped files (HTML, JSONL, JSON)
│   └── processed/           # clean, deduplicated JSONL + CSV
├── tests/
│   └── test_scraper.py      # 35 unit tests (no network required)
├── requirements.txt
└── README.md
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/endomorphosis/211-AI.git
cd 211-AI

# 2. Create a virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install the Playwright browser (Chromium)
playwright install chromium
```

---

## Usage

### Quick start — scrape everything

```bash
python -m scraper.main --mode all
```

This runs both the **static** (informational pages) and **browser** (search results) scrapers and writes clean data to `data/processed/`.

---

### Modes

| Mode | Description |
|---|---|
| `static` | Scrape informational pages (About, Programs, etc.) via HTTP |
| `browser` | Playwright-driven search across all categories × ZIP codes |
| `crawl` | BFS link-following crawl of the entire site |
| `all` | Run `static` then `browser` (default) |

### Agentic daemon + supervisor

The batch CLI above is still the safest way to run a bounded scrape. For continuous
discovery and ETL, this repo also includes a persistent agentic daemon with a
self-healing supervisor:

```bash
# One bounded pass, useful for smoke tests
python -m scraper.agentic_daemon --once --max-pages 25

# Continuous crawl/ETL loop
python -m scraper.agentic_daemon --interval 300 --max-pages 25

# Monitor the daemon and rewrite its strategy when it stalls
python -m scraper.supervisor --stale-seconds 600 --check-interval 30
```

The daemon writes heartbeat and queue state to `data/state/agentic_daemon_state.json`,
strategy controls to `data/state/daemon_strategy.json`, raw pages to
`data/raw/agentic_pages_raw.jsonl`, raw service candidates to
`data/raw/services_raw_agentic.jsonl`, and normalized outputs to
`data/processed/services_agentic.*`.

By default the daemon uses lightweight local HTTP fetching and local JSON
snapshots. To opt into the local `ipfs_datasets_py` unified web-archiving API and
dataset save tool, set `SCRAPER_ENABLE_IPFS_TOOLS=true`.

---

### Common options

```
--mode         static | browser | crawl | all   (default: all)
--categories   space-separated list; defaults to all 18 categories
--zips         space-separated list; defaults to all ~65 configured ZIPs
--no-enrich    skip per-record detail page fetches (faster, less data)
--max-pages    BFS crawl page limit                (default: 200)
--delay        seconds between requests            (default: 1.5)
--output-dir   root directory for data files       (default: data/)
--log-level    DEBUG | INFO | WARNING              (default: INFO)
```

---

### Examples

```bash
# Scrape a single category across two ZIPs (quick test)
python -m scraper.main \
    --mode browser \
    --categories food \
    --zips 97201 97401 \
    --no-enrich \
    --log-level DEBUG

# Scrape housing + food across Portland metro ZIPs
python -m scraper.main \
    --mode browser \
    --categories housing-shelter food \
    --zips 97201 97202 97203 97204 97205

# BFS site crawl (static content only)
python -m scraper.main --mode crawl --max-pages 500

# Full scrape with custom delay
python -m scraper.main --mode all --delay 2.0
```

---

## Output files

After a run, the `data/` directory contains:

| File | Contents |
|---|---|
| `raw/services_raw.jsonl` | Raw service records (one JSON object per line) |
| `raw/homepage_meta.json` | Homepage metadata, category links, iframes |
| `raw/sitemap_urls.json` | All URLs from the XML sitemap |
| `raw/static_pages_raw.json` | Raw static page data |
| `raw/robots.txt` | Site robots.txt |
| `processed/services.jsonl` | Normalised, deduplicated service records |
| `processed/services.csv` | Same data in CSV format |
| `processed/static_pages.json` | Processed static pages (no raw HTML) |

### Canonical service record schema

```json
{
  "id":              "16-char SHA-256 digest",
  "name":            "Oregon Food Bank",
  "description":     "Provides emergency food to families ...",
  "address":         "7900 NE 33rd Dr, Portland, OR 97211",
  "city":            "Portland",
  "state":           "OR",
  "zip":             "97211",
  "phone":           "503-282-0555",
  "email":           "",
  "website":         "https://www.oregonfoodbank.org",
  "hours":           "Mon–Fri 9 am–5 pm",
  "eligibility":     "Low-income households",
  "languages":       "English, Spanish",
  "categories":      "Food, Basic Needs",
  "accessibility":   "Wheelchair accessible",
  "source_url":      "https://gethelp.211info.org/resource/123",
  "search_category": "food",
  "search_zip":      "97211"
}
```

---

## Running tests

```bash
python -m pytest tests/ -v
```

All 35 tests run without network access.

---

## Configuration via environment variables

| Variable | Default | Description |
|---|---|---|
| `SCRAPER_DELAY` | `1.5` | Seconds between requests |
| `SCRAPER_MAX_RETRIES` | `3` | HTTP retry attempts |
| `SCRAPER_TIMEOUT` | `30` | Request timeout in seconds |
| `SCRAPER_HEADLESS` | `true` | Run browser headless |
| `SCRAPER_CONCURRENCY` | `2` | Concurrent browser pages |
| `SCRAPER_MAX_RESULTS` | `0` | Max results per search (0 = unlimited) |

---

## Ethical & legal notes

* The scraper respects `robots.txt` (fetched and stored at the start of each run).
* A configurable inter-request delay (default 1.5 s) limits server load.
* Data is for **non-commercial, public-benefit AI agent** purposes only.
* Contact [211info](https://www.211info.org/contact-us/) if you intend high-volume or commercial use.

---

## Roadmap

- [ ] AI agent layer (LangChain / OpenAI function-calling) on top of the scraped data
- [ ] Vector-store indexing for semantic service search
- [ ] Automatic re-scrape / delta update scheduler
- [ ] REST API exposing the processed service database
