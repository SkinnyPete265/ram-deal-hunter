"""Conservative retailer HTML product-price adapters used when JSON-LD is absent.

Only inspect explicit product-level metadata and primary price widgets.
Never infer a price from recommended products, navigation or shipping fees.
"""
import hashlib
import re

from bs4 import BeautifulSoup

MONEY_RE = re.compile(r"(?<![\d])(?:\d{1,3}(?:[.\s\u00a0]\d{3})+|\d{1,5})(?:[,.]\d{2})(?!\d)")
PRIMARY_PRICE_SELECTORS = (
    "#product .product-prices .current-price [itemprop='price']",
    "#product .product-prices .current-price .price",
    ".product-prices .current-price [itemprop='price']",
    ".product-prices .current-price .price",
    ".product-prices .current-price",
    "#our_price_display",
    ".product-info-main .price-wrapper [data-price-amount]",
    ".product-info-main .price-final_price .price",
    "#product-price .price",
    "#product-price",
    "main .product-price .price",
    "main .product-price",
    "main [itemprop='price'][content]",
)
PRICE_META_SELECTORS = (
    "meta[property='product:price:amount']",
    "meta[property='og:price:amount']",
    "meta[name='price']",
    "meta[itemprop='price']",
)


def _amount(value, convert):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{1,5}(?:[.,]\d{1,2})?", text):
        return convert(text)
    match = MONEY_RE.search(text)
    return convert(match.group()) if match else None


def _name_and_metadata(doc):
    heading = doc.select_one("h1[itemprop='name'], #product h1, main h1, h1")
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    og = doc.select_one("meta[property='og:title']")
    og_title = og.get("content", "").strip() if og else ""
    title = heading_text or og_title
    desc = doc.select_one("meta[name='description']")
    description = desc.get("content", "")[:1000] if desc else ""
    # Descriptions may establish that a 32GB package is actually 2x16GB.
    # Never parse entire page text: recommendations may be other RAM sizes.
    for selector in ("#description .product-description", ".product-description", "#product-description-short", "[itemprop='description']"):
        node = doc.select_one(selector)
        if node:
            description += " " + node.get_text(" ", strip=True)[:1200]
            break
    return title, (title + " " + description).strip()


def _primary_price(doc, convert):
    for selector in PRICE_META_SELECTORS:
        for node in doc.select(selector):
            number = _amount(node.get("content"), convert)
            if number is not None:
                return number, "Product price metadata"
    for selector in PRIMARY_PRICE_SELECTORS:
        for node in doc.select(selector):
            for key in ("content", "data-price-amount", "data-price", "value"):
                number = _amount(node.get(key), convert)
                if number is not None:
                    return number, "Primary product price"
            number = _amount(node.get_text(" ", strip=True)[:130], convert)
            if number is not None:
                return number, "Primary product price"
    return None, None


def _primary_stock(doc, classify):
    for selector in ("#product-availability", ".product-availability", "#availability", "[itemprop='availability']"):
        for node in doc.select(selector):
            content = " ".join(filter(None, [node.get("href"), node.get("content"), node.get_text(" ",strip=True)]))
            result = classify(content)
            if result != "unknown":
                return result
    for selector in ("#add-to-cart-or-refresh button", ".product-add-to-cart button", "#product .add-to-cart", "main button.add-to-cart"):
        for node in doc.select(selector):
            label = node.get_text(" ",strip=True)
            if re.search(r"\b(esgotado|indispon[ií]vel|agotado|sold\s*out)\b",label,re.I):
                return "out_of_stock"
    return "unknown"


def extract_html_offer(html, store, url, matches, price, stock, stamp):
    """Return (offer, reason). Never guess a price from a recommendation."""
    doc = BeautifulSoup(html, "html.parser")
    name, details = _name_and_metadata(doc)
    if not name:
        return None, "no_primary_product"
    kind = matches(details)
    if kind is None:
        return None, "configuration_unverified"
    unit, source = _primary_price(doc, price)
    if unit is None:
        return None, "price_not_found"
    currency = doc.select_one("meta[property='product:price:currency'], meta[itemprop='priceCurrency']")
    if currency and currency.get("content") and currency.get("content").strip().upper() != "EUR":
        return None, "non_eur_price"
    status = _primary_stock(doc, stock)
    if kind == "single_pair" and status == "in_stock":
        status = "unknown"  # Stock of one does not prove stock of two.
    total = round(unit * (2 if kind == "single_pair" else 1), 2)
    mhz = re.search(r"\b(2133|2400|2666|2933|3000|3200|3466|3600|3733|4000|4266)\b", name)
    cl = re.search(r"\bCL\s*(\d\d)\b", name, re.I)
    identity = hashlib.sha256((store + ":" + url.split("?")[0]).encode()).hexdigest()[:16]
    item = dict(
        id=identity, store=store, url=url, title=name, configuration=kind,
        units_to_buy=2 if kind=="single_pair" else 1, unit_price_eur=unit,
        price_eur=total, stock=status, shipping_to_pt="unverified",
        speed_mhz=int(mhz[1]) if mhz else None,
        cas_latency=int(cl[1]) if cl else None,
        source=source + " (HTML fallback)", observed_at=stamp(), current=True
    )
    return item, "verified_price"
