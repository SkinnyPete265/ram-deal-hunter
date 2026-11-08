# RAM Deal Hunter — Portugal

A small self-hosted desktop-DDR4 price monitor for **32 GB in exactly two 16 GB sticks**, targeting **€200 or less**. Amazon.es is prioritized as an optional Keepa source, alongside Portuguese retailers.

## Status

The repository includes working application source and GitHub Actions schedules. **A successful real-world retailer scan, GitHub-hosted public dashboard, and Telegram notifications have not yet been verified.** Stock and shipping to Portugal are not guaranteed from retailer metadata. Every deal is a **candidate** until checkout verifies the exact configuration, availability and shipping.

The repository is currently **private**. A static GitHub Pages site is not enabled by the provided scan workflow. To see results, run the dashboard locally or inspect `docs/data.json` after an Actions scan commits it.

A separate ChatGPT hourly price-watch automation was previously created. It is distinct from this project.

## Buying criteria

- Desktop DDR4 **UDIMM**, no DDR5 or laptop SO-DIMM.
- **2×16 GB kit** OR two identical **1×16 GB** units; singles are priced at twice their unit price.
- €200 product-price ceiling; add shipping at checkout. No used or dubious offers.
- Brand, MHz and CAS latency do not constrain eligibility.

## Run locally (Windows)

Install Python 3.11+ and double-click `START_WINDOWS.bat`. The application will install dependencies and start a local dashboard at **http://127.0.0.1:8765**. It attempts a scan at startup and every 30 minutes while running. Use **Scan now** for a manual check.

For command-line use:

```shell
pip install -r requirements.txt
python -m pytest -q
python monitor.py
python app.py
```

GitHub Actions uses `.github/workflows/scan.yml`, scheduled at minute 17 and 47 each hour. GitHub may delay or skip runs, especially on inactive repositories. Use **Actions → Scan RAM prices → Run workflow** to request a scan. See the **Test** workflow for automated parser tests.

## Retailers and API setup

The scanner attempts a small watchlist and category-page discovery for PCDIGA, PcComponentes, Globaldata and CHIP7; ON4TECH is also on the watchlist. Retailers frequently change HTML, URLs and access policies, so entries may fail and should not be interpreted as a full-market comparison.

Amazon.es requires a **paid Keepa API key** set as a repository Actions secret named `KEEPA_API_KEY`, or exported in your local environment. Without it, Amazon monitoring is **not configured**, and the dashboard will show this in source status. Keepa prices do not confirm eligibility to deliver to Portugal.

Optional Telegram alerts require Actions secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, or local environment variables of those names. Alerts report deal candidates, not confirmed delivered prices.

Configure secrets through **Settings → Secrets and variables → Actions → New repository secret**. Never commit tokens or keys to the repository.

## Files

- `monitor.py`: retailer scanning, safe product extraction, alert deduplication, JSON snapshot
- `amazon.py`: optional Amazon.es Keepa source
- `app.py`: local-only dashboard server and scan control
- `docs/index.html`: responsive dashboard (search, filters, CSV export)
- `docs/data.json`: last scan and historical offers
- `config.json` / `watchlist.csv`: stores and product URLs
- `tests/`: automated parser tests
- `.github/workflows/`: scheduled scan and test suite

## Accuracy and limitations

The parser only accepts explicit 2×16 GB or 1×16 GB DDR4 configurations and price data from Product JSON-LD (or Keepa); it avoids guesswork. If a store blocks requests or omits JSON-LD data, the corresponding source status will show a failure or no verified price rather than a fabricated offer. For two separate singles, a retailer's in-stock status does not establish that **two** units can be purchased. Prices and delivery costs must always be confirmed at checkout.

The scanner currently does **not** verify shipping fees or actual checkout totals to Portugal, so a €199 listing could exceed your total budget after shipping. Scanning every 30 minutes is best-effort rather than a real-time feed.
