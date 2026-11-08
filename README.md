# RAM Deal Hunter — Portugal

A small self-hosted desktop-DDR4 price monitor for **32 GB in exactly two 16 GB sticks**, targeting **€200 or less**. The scanners monitor Portugal-friendly retailers without requiring any paid price-data API.

## Status

The repository contains working application source, GitHub Actions schedules, live retailer scan data, and a successfully deployed GitHub Pages dashboard. A separate Windows home scanner was installed and has successfully uploaded recurring scans from the user's PC. Telegram delivery is not verified. Stock and shipping to Portugal are not guaranteed from retailer metadata. Every deal is a **candidate** until checkout verifies the exact configuration, availability and shipping.

The repository is **public** and includes a scheduled GitHub Pages deployment job. To activate the public dashboard, open **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**, and save. Then run **Actions → Scan RAM prices → Run workflow** to start a scan and deploy the site, or let the scheduled workflow run. After the first successful deployment, use **https://skinnypete265.github.io/ram-deal-hunter/**. The dashboard reads the latest deployed `docs/data.json`; it cannot trigger manual scans from GitHub Pages. The site is read-only and data is public, so never place API keys or Telegram tokens inside `docs/`.

A separate ChatGPT hourly price-watch automation was previously created. It is distinct from this project and is **not changed by the eight-hour GitHub/Windows schedule**.

## Buying criteria

- Desktop DDR4 **UDIMM**, no DDR5 or laptop SO-DIMM.
- **2×16 GB kit** OR two identical **1×16 GB** units; singles are priced at twice their unit price.
- €200 product-price ceiling; add shipping at checkout. No used or dubious offers.
- Brand, MHz and CAS latency do not constrain eligibility.

## Always-on Windows home scanner

Since residential connections may work where GitHub cloud runners receive HTTP 403, a **separate Windows Task Scheduler job** can scan the same public retailer pages from your home PC and upload results to `docs/local-data.json` every 8 hours. The hosted dashboard merges that home snapshot with the GitHub cloud snapshot (`docs/data.json`), preserving distinct timestamps, scan origins, and stale indicators. A snapshot remains current for up to **12 hours** to tolerate schedule delays; missed scans become stale. The cloud scanner runs three times per day at 02:17, 10:17 and 18:17 UTC. GitHub cron timing is best-effort.

**Upgrading an existing 30-minute Windows installation:** The installed task updates itself to an eight-hour interval when `Run-LocalScan.ps1` pulls the new `Update-LocalSchedule.ps1` helper. Because an already-running PowerShell process uses the old script version, the change may require up to **two more half-hour task executions** to take effect. Check Task Scheduler → **RAM Deal Hunter - Home Scanner** → Triggers; it should eventually show an eight-hour repetition. The installer now creates eight-hour tasks directly. This does not guarantee previously blocked stores will work from home.

**One-time setup on your Windows computer:**

1. Install **Python 3.11+** and **Git for Windows** (with Git Credential Manager). The `py -3` and `git` commands must work in PowerShell.
2. **Clone** [SkinnyPete265/ram-deal-hunter](https://github.com/SkinnyPete265/ram-deal-hunter) using GitHub Desktop (`Code → Open with GitHub Desktop`) or `git clone https://github.com/SkinnyPete265/ram-deal-hunter.git`. A downloaded ZIP is not enough because the scanner uploads through Git.
3. In the cloned folder, double-click **`INSTALL_BACKGROUND_SCANNER.bat`**. The installer installs Python packages, performs a real scan and attempts a Git push. **Sign into GitHub when Git Credential Manager prompts you.** A failed first push prevents the background task from being registered.
4. If the initial upload succeeds, Windows Task Scheduler registers **RAM Deal Hunter - Home Scanner**, running every **8 hours**. It works while the PC is locked, but the Windows user must remain **signed in**, the PC must be awake, and its network must be online.
5. Visit [the public dashboard](https://skinnypete265.github.io/ram-deal-hunter/) after the **Publish Home PC RAM dashboard** GitHub Actions workflow deploys the first upload. The page shows **Home PC** as a scan source.

**Tools:** Double-click `RUN_LOCAL_SCAN.bat` for an interactive scan; when it finishes (including after an error), press **Y** to scan again or **N** to close. The same window is reused for repeated tests. This prompt is exclusive to the manual `.bat` launcher; the unattended scheduled task continues to run every eight hours without any input. Because the launcher updates its own files from GitHub during a scan, you may need to close and reopen the old launcher **once** to see the new prompt after this change. Double-click `UNINSTALL_BACKGROUND_SCANNER.bat` to remove the scheduled task. Inspect `logs/local-scanner.log` for errors (local-only; ignored by Git). If Git credentials are revoked, sign in again through an interactive manual scan. **Don't run `START_WINDOWS.bat` alongside the scheduled scanner** unless you know how to manage its separate local data and Git checkout changes.

**Privacy/security:** Only public product listings, prices, source statuses and timestamps are committed. Do not add personal files, authentication cookies or secrets to `docs/`. The installer uses your existing Git credential manager rather than embedding access tokens. This design does **not** run a self-hosted GitHub Actions runner on your PC, an avoidable security risk for a public repository.

## Run locally (Windows)

Install Python 3.11+ and double-click `START_WINDOWS.bat`. The application will install dependencies and start a local dashboard at **http://127.0.0.1:8765**. It attempts a scan at startup and every 8 hours while running. Use **Scan now** for a manual check.

For command-line use:

```shell
pip install -r requirements.txt
python -m pytest -q
python monitor.py
python app.py
```

GitHub Actions uses `.github/workflows/scan.yml`, scheduled at 02:17, 10:17 and 18:17 UTC (and on changes to retailer configuration, watchlists, or the scan workflow). GitHub may delay or skip runs, especially on inactive repositories. Use **Actions → Scan RAM prices → Run workflow** to request a scan. See the **Test** workflow for automated parser tests.

## Retailers and API setup

The scanner uses a small seeded watchlist plus category-page discovery across **PCDIGA, PcComponentes, Globaldata, CHIP7, Novo Atalho, Castro Electrónica, Chipman, You Get, KIBO, El Shop (Spain), and PCBox**. Additional direct-product watchlist URLs cover **ON4TECH, Switch Technology, and Fnac.pt**. The Spain-based El Shop explicitly lists Portugal as a supported destination; other included retailers have Portuguese storefronts and/or published Portugal delivery options. Marketplace shipping depends on the individual seller.

**PcComponentes primary-price fix:** The Windows scanner's saved diagnostics revealed actual `#pdp-price-current-container`, `#pdp-price-current-integer` and `#pdp-price-current-decimals` element IDs, sometimes formatted with spaces (e.g. `185 , 00 €`). The dedicated parser now reads that main buybox before attempting a slower browser render. The 8 November 2026 home scan confirmed this fix recovers 12 PcComponentes prices and correctly identifies several out-of-stock offers. CHIP7 sometimes publishes no online checkout price and asks buyers to contact a shop. When its primary page contains a consistent PVP within a credit simulation, this is shown only as an **indicative financing reference**, not a verified buy-now price, with stock unknown and all alerts disabled. Missing PVP is reported as **contact store for price**, not a parser error. Castro Electrónica can intermittently return 502 gateway errors and timeouts; the scanner performs one normal retry and then, on failure, one independent TLS-client attempt. If both fail, no new price is claimed. An obsolete PcComponentes URL returning HTTP 410 was removed from the watchlist.

**Windows-only JavaScript fallback (optional):** Some PcComponentes and CHIP7 product pages do not expose their main buybox price in raw HTML. For up to six failed PcComponentes products and three CHIP7 products per home scan, the scanner may use the installed Chrome or Edge executable in isolated headless mode to read the JavaScript-rendered DOM. No browser extension, paid proxy, extra Python package or account is needed. Only the verified primary-product price is eligible; the parser never substitutes a related-item price. This feature may still fail because a retailer blocks automation or does not show a valid buybox. It is not used on GitHub's Linux runners.

**Known coverage gaps:** PCDIGA, PcComponentes and CHIP7 returned HTTP 403 from GitHub-hosted scans on 8 November 2026. The monitor now retries a 403/429 **once** using the free open-source `curl_cffi` client with a Chrome-like TLS/HTTP2 fingerprint. It records recovery counts and blocked status, then skips further attempts to a persistently blocked store *during the same run*. This cannot solve CAPTCHA or JavaScript verification challenges, and GitHub's hosting IP may still be denied. No paid proxies, CAPTCHA-solving services or retailer accounts are required. Do not infer that a retailer is successfully covered until its latest scan reports prices. Other sources may omit structured product data or block requests too. The tracker does not claim total market coverage.

The scanner first checks product JSON-LD and falls back to **retailer-specific HTML price extraction** where needed, including Chipman's custom sale price, Castro Electrónica's **online** price (not the physical-shop price), ON4TECH's primary product price and Fnac's marketplace offer. It also reads explicitly matching *catalogue cards* on Chipman, Castro Electrónica and selected other sites; these are marked **catalogue prices / stock unverified** until their product pages establish stock. A product link alone is not sufficient. Product descriptions and known manufacturer SKUs help verify exactly two 16 GB desktop DDR4 modules; 2×8 GB kits, single 32 GB sticks, DDR5 and SO-DIMMs are excluded. The public dashboard distinguishes incomplete configurations from actual price-extraction failures and marks old observations stale.

**Free comparison fallback:** The scanner also attempts a public DDR4 32 GB category listing on KuantoKusta. Matching 2×16 GB listings are recorded as **comparison-only price candidates**, separate from direct store offers. These are the cheapest advertised prices from one or more sellers; they do **not** establish the actual seller, current stock, checkout shipping to Portugal, or final amount. The price and configuration must be checked on the comparison product page and with the actual seller. This indirect channel may surface offers from blocked shops, but it is **not** a direct monitor for those shops. The comparison site may also reject automated requests; in that case its source status shows an error.

**Amazon.es is deliberately excluded from unattended GitHub scans.** Reliable automated Amazon prices and delivery-to-Portugal checks are not provided by this free scanner, and no Keepa subscription is required. You can still search Amazon.es manually or use the separate ChatGPT hourly watch for best-effort public web listing research. These results should never be interpreted as confirmed checkout totals.

Optional Telegram alerts require Actions secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, or local environment variables of those names. Alerts are now restricted to **direct retailer listings of in-stock 2×16 GB kits priced at €200 or less**. Unknown-stock items, two separate singles, catalogue-only estimates, CHIP7 finance-only PVP and KuantoKusta comparison prices do **not** trigger them. Retailer-reported stock still does not prove final checkout availability or delivered cost.

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

The scanner accepts explicitly specified 2×16 GB kits or eligible 1×16 GB modules (priced as two identical units) and certain **unambiguous manufacturer part numbers** proving those configurations. Prices must originate from the primary product data, current sale-price widget, or a single corresponding catalogue card—never recommended products, crossed-out list prices, shipping fees, or other product offers. If data remains inaccessible, it reports the reason, rather than inventing a price. On up to two failed product pages per retailer, limited **public, sanitized price-element diagnostics** are included in each snapshot to help improve adapters without saving full HTML, forms or credentials. For two separate singles, a retailer's in-stock status does not establish that **two** units can be purchased. Prices and delivery costs must always be confirmed at checkout.

The scanner currently does **not** verify shipping fees or actual checkout totals to Portugal, so a €199 listing could exceed your total budget after shipping. Scanning every 8 hours is best-effort rather than a real-time feed.
