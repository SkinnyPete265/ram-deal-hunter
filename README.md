# RAM Deal Hunter — Portugal

A small self-hosted desktop-DDR4 price monitor for **32 GB in exactly two 16 GB sticks**, targeting **€200 or less**. The automatic scanner targets Portuguese retailers without requiring any paid price-data API.

## Status

The repository contains working application source, GitHub Actions schedules, live retailer scan data, and a successfully deployed GitHub Pages dashboard. A separate Windows home scanner is available but has not been installed or tested on the user's PC. Telegram delivery is not verified. Stock and shipping to Portugal are not guaranteed from retailer metadata. Every deal is a **candidate** until checkout verifies the exact configuration, availability and shipping.

The repository is **public** and includes a scheduled GitHub Pages deployment job. To activate the public dashboard, open **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**, and save. Then run **Actions → Scan RAM prices → Run workflow** to start a scan and deploy the site, or let the scheduled workflow run. After the first successful deployment, use **https://skinnypete265.github.io/ram-deal-hunter/**. The dashboard reads the latest deployed `docs/data.json`; it cannot trigger manual scans from GitHub Pages. The site is read-only and data is public, so never place API keys or Telegram tokens inside `docs/`.

A separate ChatGPT hourly price-watch automation was previously created. It is distinct from this project.

## Buying criteria

- Desktop DDR4 **UDIMM**, no DDR5 or laptop SO-DIMM.
- **2×16 GB kit** OR two identical **1×16 GB** units; singles are priced at twice their unit price.
- €200 product-price ceiling; add shipping at checkout. No used or dubious offers.
- Brand, MHz and CAS latency do not constrain eligibility.

## Always-on Windows home scanner

Since residential connections may work where GitHub cloud runners receive HTTP 403, a **separate Windows Task Scheduler job** can scan the same public retailer pages from your home PC and upload results to `docs/local-data.json` every 30 minutes. The hosted dashboard merges that home snapshot with the GitHub cloud snapshot (`docs/data.json`), preserving distinct timestamps, scan origins, and stale indicators. This does not guarantee previously blocked stores will work from home.

**One-time setup on your Windows computer:**

1. Install **Python 3.11+** and **Git for Windows** (with Git Credential Manager). The `py -3` and `git` commands must work in PowerShell.
2. **Clone** [SkinnyPete265/ram-deal-hunter](https://github.com/SkinnyPete265/ram-deal-hunter) using GitHub Desktop (`Code → Open with GitHub Desktop`) or `git clone https://github.com/SkinnyPete265/ram-deal-hunter.git`. A downloaded ZIP is not enough because the scanner uploads through Git.
3. In the cloned folder, double-click **`INSTALL_BACKGROUND_SCANNER.bat`**. The installer installs Python packages, performs a real scan and attempts a Git push. **Sign into GitHub when Git Credential Manager prompts you.** A failed first push prevents the background task from being registered.
4. If the initial upload succeeds, Windows Task Scheduler registers **RAM Deal Hunter - Home Scanner**, running every **30 minutes**. It works while the PC is locked, but the Windows user must remain **signed in**, the PC must be awake, and its network must be online.
5. Visit [the public dashboard](https://skinnypete265.github.io/ram-deal-hunter/) after the **Publish Home PC RAM dashboard** GitHub Actions workflow deploys the first upload. The page shows **Home PC** as a scan source.

**Tools:** Double-click `RUN_LOCAL_SCAN.bat` for an interactive scan, or `UNINSTALL_BACKGROUND_SCANNER.bat` to remove the scheduled task. Inspect `logs/local-scanner.log` for errors (local-only; ignored by Git). If Git credentials are revoked, sign in again through an interactive manual scan. **Don't run `START_WINDOWS.bat` alongside the scheduled scanner** unless you know how to manage its separate local data and Git checkout changes.

**Privacy/security:** Only public product listings, prices, source statuses and timestamps are committed. Do not add personal files, authentication cookies or secrets to `docs/`. The installer uses your existing Git credential manager rather than embedding access tokens. This design does **not** run a self-hosted GitHub Actions runner on your PC, an avoidable security risk for a public repository.

## Run locally (Windows)

Install Python 3.11+ and double-click `START_WINDOWS.bat`. The application will install dependencies and start a local dashboard at **http://127.0.0.1:8765**. It attempts a scan at startup and every 30 minutes while running. Use **Scan now** for a manual check.

For command-line use:

```shell
pip install -r requirements.txt
python -m pytest -q
python monitor.py
python app.py
```

GitHub Actions uses `.github/workflows/scan.yml`, scheduled at minute 17 and 47 each hour (with an additional scan on changes to scanner source/configuration). GitHub may delay or skip runs, especially on inactive repositories. Use **Actions → Scan RAM prices → Run workflow** to request a scan. See the **Test** workflow for automated parser tests.

## Retailers and API setup

The scanner uses a small seeded watchlist plus category-page discovery across **PCDIGA, PcComponentes, Globaldata, CHIP7, Novo Atalho, Castro Electrónica, Chipman, You Get, KIBO, El Shop (Spain), and PCBox**. Additional direct-product watchlist URLs cover **ON4TECH, Switch Technology, and Fnac.pt**. The Spain-based El Shop explicitly lists Portugal as a supported destination; other included retailers have Portuguese storefronts and/or published Portugal delivery options. Marketplace shipping depends on the individual seller.

**Known coverage gaps:** PCDIGA, PcComponentes and CHIP7 returned HTTP 403 from GitHub-hosted scans on 8 November 2026. The monitor now retries a 403/429 **once** using the free open-source `curl_cffi` client with a Chrome-like TLS/HTTP2 fingerprint. It records recovery counts and blocked status, then skips further attempts to a persistently blocked store *during the same run*. This cannot solve CAPTCHA or JavaScript verification challenges, and GitHub's hosting IP may still be denied. No paid proxies, CAPTCHA-solving services or retailer accounts are required. Do not infer that a retailer is successfully covered until its latest scan reports prices. Other sources may omit structured product data or block requests too. The tracker does not claim total market coverage.

The scanner checks direct product pages for Product JSON-LD, and accepts only explicitly qualifying RAM configurations. A product link found on a category page is **not** considered a verified offer until the product page independently proves its specification, price and stock status. The public dashboard reports failed source checks and keeps old observations marked stale.

**Free comparison fallback:** The scanner also attempts a public DDR4 32 GB category listing on KuantoKusta. Matching 2×16 GB listings are recorded as **comparison-only price candidates**, separate from direct store offers. These are the cheapest advertised prices from one or more sellers; they do **not** establish the actual seller, current stock, checkout shipping to Portugal, or final amount. The price and configuration must be checked on the comparison product page and with the actual seller. This indirect channel may surface offers from blocked shops, but it is **not** a direct monitor for those shops. The comparison site may also reject automated requests; in that case its source status shows an error.

**Amazon.es is deliberately excluded from unattended GitHub scans.** Reliable automated Amazon prices and delivery-to-Portugal checks are not provided by this free scanner, and no Keepa subscription is required. You can still search Amazon.es manually or use the separate ChatGPT hourly watch for best-effort public web listing research. These results should never be interpreted as confirmed checkout totals.

Optional Telegram alerts require Actions secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, or local environment variables of those names. Alerts report deal candidates, not confirmed delivered prices.

Configure secrets through **Settings → Secrets and variables → Actions → New repository secret**. Never commit tokens or keys to the repository.

## Files

- `monitor.py`: retailer scanning, safe product extraction, alert deduplication, JSON snapshot
- `app.py`: local-only dashboard server and scan control
- `docs/index.html`: responsive dashboard (search, filters, CSV export)
- `docs/data.json`: last scan and historical offers
- `config.json` / `watchlist.csv`: allowed retailers, category URLs, and direct product URLs
- `tests/`: automated parser tests
- `.github/workflows/`: scheduled scan and test suite

## Accuracy and limitations

The parser only accepts explicit 2×16 GB or 1×16 GB DDR4 configurations and price data from retailer Product JSON-LD; it avoids guesswork. If a store blocks requests or omits JSON-LD data, the corresponding source status will show a failure or no verified price rather than a fabricated offer. For two separate singles, a retailer's in-stock status does not establish that **two** units can be purchased. Prices and delivery costs must always be confirmed at checkout.

The scanner currently does **not** verify shipping fees or actual checkout totals to Portugal, so a €199 listing could exceed your total budget after shipping. Scanning every 30 minutes is best-effort rather than a real-time feed.
