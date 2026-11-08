# RAM Deal Hunter · Portugal

A starter price monitor with a real, responsive dashboard, a scheduled GitHub Actions runner, optional Amazon.es monitoring via Keepa, optional broad discovery via SerpApi Google Shopping, price history, and Telegram deal-candidate alerts.

## Exact purchasing goal

- **32 GB DDR4 in exactly 2 sticks of 16 GB**.
- A **2×16 GB kit** (one retail package) or **two units of the same 1×16 GB RAM SKU** (2 units in the basket) is acceptable. For singles, reported price is `2 × unit price`.
- €200 maximum *combined product price* in this first version. Portuguese shipping, taxes/fees, and availability of two single modules are **not automatically verified**. An alert is explicitly a candidate, never a guarantee that final checkout is ≤€200.
- Default **desktop UDIMM** only. If this is for a laptop, edit `config.json` → `form_factor: "SODIMM"` before running. Never mix SO-DIMM and UDIMM.
- Brand and speed unrestricted. Stock unknown is explicitly labeled, and can be excluded from alerts.

## Current state and limitations

**This is working source code / a deployable starter, not an already-running service.** Tests pass against synthetic HTML, but retailer live pages have not been tested from this environment. Websites change markup, block scripts, or hide data in JavaScript. A product price is only recorded from `schema.org` product-level JSON-LD; if a retailer does not expose trustworthy structured pricing, it is logged as `no_verified_price` rather than guessed. Category discovery only catches anchors containing exact configurations and therefore does not exhaust the catalog. It currently covers named sites, not literally every shop in Europe.

Amazon.es is monitored via **Keepa** if a paid Keepa API key is supplied (`KEEPA_API_KEY`). The scanner searches Amazon Spain twice every 6 hours and rechecks discovered ASINs on each scheduled scan. Amazon's reported price and stock **do not establish shipping eligibility or checkout total to Portugal**. Keepa API requests consume tokens and incur a subscription cost. **SerpApi** (`SERPAPI_API_KEY`) is optional and paid; it helps discover further retailer offers from Google Shopping Portugal; not all results link directly to the seller, so coverage is incomplete.

No unauthorized Amazon scraping, CAPTCHA bypass, proxy rotation, or aggressive requests are used. Respect store terms and robots policies when expanding adapters.

## Easy Windows launch (no Codex needed)

1. Unzip the project to a permanent folder on your desktop PC (avoid extracting it inside Downloads if you intend to schedule scans).
2. Install **Python 3.11 or newer** from [python.org](https://www.python.org/downloads/). Enable **Add Python to PATH** during setup.
3. Double-click **`START_WINDOWS.bat`**. On the first run it creates an isolated Python environment, installs dependencies, launches the local dashboard at **http://127.0.0.1:8765**, and begins a scan. Use **Scan now** to request another check. Subsequent checks run approximately every 30 minutes **while the launcher is open**.
4. Optional: to check every 30 minutes in the background when the PC is turned on (without keeping the dashboard open), right-click **`INSTALL_BACKGROUND_SCANS.ps1` → Run with PowerShell**. This creates a Windows Task Scheduler task named **RAM Deal Hunter Scan**. Windows may require a one-time approval and script execution policy configuration. To remove it, run **`UNINSTALL_BACKGROUND_SCANS.ps1`**.
5. Optional: configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as environment variables to receive alerts from the local scanner. Without them, the scanner stores results but sends **no local Telegram messages**.

**Do not run both the open dashboard scanner and the Task Scheduler scanner unnecessarily**: that doubles requests. The separate ChatGPT hourly deal watch is already scheduled independently and does not share local scan history. A Windows PC must be powered on for the local scheduled task to run.

Retailer page monitoring is still best-effort and may fail or return no verified prices, especially on JavaScript-heavy or bot-protected sites. Amazon.es availability requires a properly configured Keepa integration; there is no free comprehensive Amazon scraper in this version.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python monitor.py
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. The dashboard loads `docs/data.json` and shows the exact time of the last scan. Data is **not** live until `monitor.py` has successfully run with actual network access.

Environment variables (optional): `KEEPA_API_KEY`, `SERPAPI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Never commit keys.

## Run continuously on GitHub

1. Create a repository for the source files, preserving the `.github/workflows/scan.yml` folder. For GitHub Pages on a GitHub Free account, a **public repository** is the straightforward route (the dashboard would then be public). A private deployment may have different plan requirements.
2. In **Settings → Actions → General**, allow GitHub Actions and use suitable workflow permissions; the YAML requests `contents: write` to commit price snapshots and Pages permissions to deploy the dashboard.
3. In **Settings → Pages**, choose **GitHub Actions** as the build/deployment source.
4. In **Settings → Secrets and variables → Actions**, add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and optionally `KEEPA_API_KEY`, `SERPAPI_API_KEY`. Get the Telegram token from **@BotFather** and your chat ID by messaging your bot and reading its `getUpdates` API response. Never paste your bot token into a chat, webpage, or repository.
5. In the **Actions** tab, run **Check RAM prices → Run workflow** once manually. Inspect logs, confirm `docs/data.json` has current observations and not solely retailer errors, and visit the URL on **Settings → Pages**.
6. The workflow is scheduled at **:17 and :47 UTC**, nominally every 30 minutes. GitHub can **delay or skip** scheduled workflows, especially under load; this is near-real-time polling, not an always-on live stream. For high-reliability minute-level tracking, use a dedicated server/worker and a queue instead.
7. Review errors and keep selectors, categories, and retailer permissions up to date. GitHub may disable scheduled workflows in inactive public repositories.

## Alerts

- Trigger when a currently observed qualifying offer is first seen at ≤€200 or drops a further €5 below the last alerted price.
- Unknown-stock offers can trigger **clearly labeled candidate alerts** (`include_unknown_stock_candidates: true`); set this to `false` for stock-confirmed notifications only.
- Exclude explicitly sold-out listings. Previously observed listings go stale when a fresh fetch fails; stale data never triggers an alert.
- Keep `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in repository secrets. Without secrets, alerts are not sent; they are **not** queued for later delivery.
- Alerts state that shipping to Portugal and the final checkout price are **unverified**.

## Data and customization

- `config.json`: budget, default physical module type, store category pages, paid search queries, scan limits.
- `watchlist.csv`: exact product URLs to try on every scan; add your own trusted retailer product URLs, and update `STORE_HOSTS` in `monitor.py` as needed.
- `monitor.py`: request/parsing/qualification/deduplication/history/alerting.
- `docs/data.json`: observations and price-change history; persisted by scheduled commits; no dummy results are inserted into the dashboard.
- `docs/index.html`: standalone dark dashboard. Search, filter by retailer, change sorting, view kit specs and stock confidence, price-history sparklines, export CSV, and click through to sellers.
- `tests/test_monitor.py`: sanity checks preventing single 32 GB/4×8 GB/DDR5 products from being mistaken for 2×16 GB.
- `CODEX_PROMPT.md`: prompt for Codex to harden and finish a fully maintained production deployment.

### Priority improvements for production

- Verify actual retailer page markup and implement tested site-specific JSON/network adapters with store-level health reporting.
- Validate shipping and **final delivered price** to Portugal (where possible via published delivery tables or APIs, not by placing orders).
- Add a manual seller trust/allowlist and independent stock checks (at least 2 for single modules).
- Improve full-category discovery and retailer coverage, including permitted product feeds and KuantoKusta source links.
- Prevent price-index stale values from being mistaken for checkout-ready listings; derive a confidence score per offer.
- Create a cheap fallback for Amazon.es if you don't want a paid API. Any fallback must be approved/permitted, clearly caveated, and actually tested.

**No purchases are made automatically.** You must verify compatibility with your motherboard/CPU, including UDIMM versus SO-DIMM, DDR4 voltage, and kit specifications, before ordering.