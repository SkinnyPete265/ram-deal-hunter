"""Conservative retailer HTML product-price adapters used when JSON-LD is absent.

Only inspect explicit product-level metadata and primary price widgets.
Never infer a price from recommended products, navigation or shipping fees.
"""
import hashlib
import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
    "main [itemprop='price'][content]",
)
# Verified by inspecting real public product-page markup.
# Do not use unscoped .price or .product-price: related products also use them.
STORE_PRICE_SELECTORS = {
    "Chipman": (
        "main [class*='text-3xl'][class*='text-sale-']",
        "main [class*='text-xl'][class*='text-sale-']",
        "main [class*='text-3xl'][class*='font-extrabold']",
    ),
    "Castro Electrónica": (
        "span.product-opportunity-new-price",
        ".product-opportunity-new-price",
    ),
    "ON4TECH": (
        "span.product-detalhe-price",
        ".product-detalhe-price",
    ),
    "Globaldata": ("span.sales.js-sales", "span.sales .value"),
    "Fnac": (".f-faPriceBox__price.userPrice", ".f-faPriceBox__price"),
    "KIBO": (".kibo-pdp-price__amount",),
    "El Shop": (".product__prices-inline .product__price", ".product__prices-inline"),
    "PCBox": (".space-y-6 .text-xl.font-bold",),
    # PcComponentes renders a React purchase box. These attributes are
    # main-product selectors, unlike its unrelated product-card__price lists.
    "PcComponentes": (
        "[data-e2e='pdp-price-current']",
        "[data-e2e='pdp-price-current-amount']",
        "[data-e2e='pdp-price']",
    ),
}

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


def _pccomponentes_price(doc, convert):
    """Extract PcComponentes' primary PDP price without touching recommendation cards.

    Live home-PC diagnostics (2026-11-08) show the main-price IDs
    #pdp-price-section, #pdp-price-current-container, and nested integer/
    decimals spans. The visible text is sometimes spaced: "185 , 00 €".
    """
    section = doc.select_one("#pdp-price-section")
    container = section.select_one("#pdp-price-current-container") if section else None
    if container is None:
        container = doc.select_one("#pdp-price-current-container")
    if container is not None:
        raw = container.get_text(" ", strip=True).replace("\u00a0", " ")
        amounts = re.findall(r"(?<!\d)(\d{1,5})\s*[,\.]\s*(\d{2})\s*(?:€|EUR)", raw, re.I)
        # Euro sign isn't a word character, so also support it explicitly.
        if not amounts:
            amounts = re.findall(r"(?<!\d)(\d{1,5})\s*[,\.]\s*(\d{2})\s*€", raw)
        if len(amounts) == 1:
            number = convert(amounts[0][0] + "." + amounts[0][1])
            if number is not None:
                return number
        # Reject ambiguous containers containing multiple different prices.
        if len(set(amounts)) > 1:
            return None

    parent = section or doc
    integer = parent.select_one("#pdp-price-current-integer, [data-e2e='pdp-price-current-integer']")
    decimals = parent.select_one(
        "#pdp-price-current-decimals, #pdp-price-current-decimal, "
        "[data-e2e='pdp-price-current-decimals'], [data-e2e='pdp-price-current-decimal']"
    )
    if integer is None or decimals is None:
        return None
    # Prefer the *direct* text node for the integer because the decimal may
    # be nested inside it in the storefront's React markup.
    direct = " ".join(str(node).strip() for node in integer.find_all(string=True, recursive=False))
    whole = re.sub(r"[^0-9]", "", direct)
    cents = re.search(r"[,\.]?\s*(\d{2})", decimals.get_text(" ", strip=True))
    if not (1 <= len(whole) <= 5 and cents):
        return None
    return convert(whole + "." + cents.group(1))

def _primary_price(doc, convert, store=None):
    for selector in PRICE_META_SELECTORS:
        for node in doc.select(selector):
            number = _amount(node.get("content"), convert)
            if number is not None:
                return number, "Product price metadata"
    if store=="PcComponentes":
        number=_pccomponentes_price(doc,convert)
        if number is not None:
            return number, "PcComponentes primary buybox price"
    for selector in STORE_PRICE_SELECTORS.get(store,()) + PRIMARY_PRICE_SELECTORS:
        for node in doc.select(selector):
            for key in ("content", "data-price-amount", "data-price", "value"):
                number = _amount(node.get(key), convert)
                if number is not None:
                    return number, "Primary product price"
            number = _amount(node.get_text(" ", strip=True)[:130], convert)
            if number is not None:
                return number, "Primary product price"
    return None, None


def _chipman_tax_price(doc, convert):
    """Fallback for Chipman product pages showing '189,90 € Com IVA'.

    Only inspect the product text immediately following the main heading,
    never unrelated recommendation cards elsewhere on the page.
    """
    main = doc.select_one("#product") or doc.select_one("#main") or doc.select_one("main")
    if main is None:
        return None
    heading = main.select_one("h1")
    if heading is None:
        return None
    full = main.get_text(" ", strip=True)
    name = heading.get_text(" ", strip=True)
    start = full.find(name)
    if start < 0:
        return None
    excerpt = full[start + len(name):start + len(name) + 1800]
    # Prefer the price immediately followed by the product's VAT label.
    for match in re.finditer(r"(?<!\d)(\d{1,5}(?:[.,]\d{2}))\s*€\s*Com\s+IVA\b",excerpt,re.I):
        number = _amount(match.group(1),convert)
        if number is not None:
            return number
    return None


def category_card_offers(html, store, base, matches, price, stock, stamp, allowed):
    """Read retailer-owned catalogue prices, never shipping charges or recommendations.

    Catalogue price alone never establishes stock or delivery. If a later
    product page yields structured data it replaces this provisional observation.
    """
    doc=BeautifulSoup(html,"html.parser")
    found={}
    # Restrict format inference to an explicitly DDR4-only retailer category.
    ddr4_category=bool(re.search(r"(?:ddr4|memorias-ram-ddr4)",base,re.I))

    def add(anchor, price_node, card):
        if anchor is None or price_node is None:
            return
        href=anchor.get("href","")
        url=urljoin(base,href).split("#")[0].split("?")[0]
        if not allowed(store,url) or url.rstrip("/")==base.rstrip("/"):
            return
        name=anchor.get_text(" ",strip=True)
        if not name:
            heading=card.select_one(".product-title, h2, h3")
            name=heading.get_text(" ",strip=True) if heading else ""
        if not name or len(name)>230:
            return
        description=card.select_one(".product-description,.product-desc")
        details=name+(" "+description.get_text(" ",strip=True)[:350] if description else "")
        if ddr4_category and "ddr4" not in details.lower():
            details+=" DDR4"
        kind=matches(details)
        if kind is None:
            return
        unit=None
        for value in (price_node.get("content"),price_node.get("data-price-amount"),
                      price_node.get_text(" ",strip=True)[:110]):
            unit=_amount(value,price)
            if unit is not None:
                break
        if unit is None:
            return
        status="unknown"
        indicator=card.select_one(".product-availability,.out-of-stock,.product-flags .out_of_stock")
        if indicator and stock(indicator.get_text(" ",strip=True))=="out_of_stock":
            status="out_of_stock"
        total=round(unit*(2 if kind=="single_pair" else 1),2)
        ident=hashlib.sha256((store+":"+url).encode()).hexdigest()[:16]
        mhz=re.search(r"\b(2133|2400|2666|2933|3000|3200|3466|3600|3733|4000|4266)\b",name)
        cl=re.search(r"\bCL\s*(\d\d)\b",name,re.I)
        found[ident]=dict(id=ident,store=store,url=url,title=name,configuration=kind,
            units_to_buy=2 if kind=="single_pair" else 1,
            unit_price_eur=unit,price_eur=total,stock=status,
            shipping_to_pt="unverified",speed_mhz=int(mhz[1]) if mhz else None,
            cas_latency=int(cl[1]) if cl else None,
            source="Retailer catalogue price (verify product page)",observed_at=stamp(),
            current=True,catalogue_only=True)

    generic=("article.product-miniature",".product-miniature",".product-card",
             ".product-item",".js-product-miniature","li.ajax_block_product")
    for card in doc.select(", ".join(generic)):
        anchor=card.select_one("h2.product-title a[href], h3.product-title a[href], .product-title a[href], a.product-name[href], a.product-thumbnail[href]")
        node=card.select_one(".product-price-and-shipping .price:not(.regular-price),.current-price .price,.price-final_price .price,.product-price,.price:not(.regular-price)")
        add(anchor,node,card)

    if store=="El Shop":
        # Current PrestaShop-derived cards use product-miniature__price
        # and absolute product links instead of .product-title anchors.
        for card in doc.select("article.product-miniature"):
            anchor=next((a for a in card.select("a[href]") if
                         len(a.get_text(" ",strip=True))>12 and
                         ("ddr4" in a.get_text(" ",strip=True).lower() or
                          "sodimm" in a.get_text(" ",strip=True).lower())),None)
            node=card.select_one(".product-miniature__prices .product-miniature__price")
            add(anchor,node,card)

    if store=="Chipman":
        # Current custom Tailwind storefront: <article class="group card-hover">
        # contains an image link, a second named link, a struck-out price and
        # a visible sale-price span with text-sale-600.
        for card in doc.select("article.card-hover"):
            anchor=next((a for a in card.select("a[href]") if
                         "/memorias-ram-ddr4/" in a.get("href","") and
                         len(a.get_text(" ",strip=True))>18),None)
            node=card.select_one("span[class*='text-sale-'][class*='font-black']")
            if node is None:
                node=card.select_one("span[class*='text-sale-']")
            add(anchor,node,card)

    if store=="Castro Electrónica":
        # The retailer's online price uses span.price-web; a different
        # nearby "Loja" amount refers to the in-store price.
        for node in doc.select("span.price-web"):
            parent=node
            for _ in range(9):
                parent=parent.parent
                if parent is None:
                    break
                links=[a for a in parent.select("a[href]")
                       if "/pt/product/" in a.get("href","")]
                links=[a for a in links if len(a.get_text(" ",strip=True))>16]
                if not links:
                    continue
                anchor=max(links,key=lambda a:len(a.get_text(" ",strip=True)))
                add(anchor,node,parent)
                break
    return list(found.values())


def _chip7_financing_pvp(doc, convert):
    """Indicative amount only: CHIP7 sometimes lists PVP in a credit simulation.

    Require the PVP and the financed amount to agree, within the main product
    heading's nearby text. Credit terms aren't a confirmed checkout price;
    the resulting offer must be explicitly flagged and stock unverified.
    """
    main=doc.select_one("main") or doc.select_one("#main") or doc.body
    if main is None:
        return None
    heading=main.select_one("h1")
    if heading is None:
        return None
    text=main.get_text(" ",strip=True)
    label=heading.get_text(" ",strip=True)
    pos=text.find(label)
    if pos<0:
        return None
    near=text[pos+len(label):pos+len(label)+2600]
    if not re.search(r"Cr[eé]dito\s*/\s*Presta[cç][oõ]es", near,re.I):
        return None
    if not re.search(r"Contacte\s+a\s+loja\s+CHIP7",near,re.I):
        return None
    pvp=re.findall(r"\bPVP\s+(\d{1,5}[.,]\d{2})\s*€",near,re.I)
    financed=re.findall(r"Montante\s+Financiado\s+(\d{1,5}[.,]\d{2})\s*€",near,re.I)
    amounts={convert(v) for v in pvp if convert(v) is not None}
    financed_amounts={convert(v) for v in financed if convert(v) is not None}
    if len(amounts)!=1 or amounts!=financed_amounts:
        return None
    return amounts.pop()


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


def _pccomponentes_stock(doc):
    """Identify explicit *unavailable* main-item wording on PcComponentes.

    A visible price without a purchase option is not evidence of stock.
    Only examine the portion immediately after the primary h1, rather than
    unrelated product cards appearing later on the page.
    """
    main=doc.select_one("main") or doc.body
    if main is None:
        return "unknown"
    heading=main.select_one("h1")
    if heading is None:
        return "unknown"
    full=main.get_text(" ",strip=True)
    label=heading.get_text(" ",strip=True)
    position=full.find(label)
    if position<0:
        return "unknown"
    primary=full[position+len(label):position+len(label)+2500]
    if re.search(
        r"disponibilidade\s+do\s+produto\s*"
        r"(?:sem\s+data\s+exacta\s+de\s+chegada|sem\s+data\s+exata\s+de\s+chegada)",
        primary, re.I
    ):
        return "out_of_stock"
    if re.search(r"avisem[- ]me\s+quando\s+estiver\s+dispon[ií]vel",primary,re.I):
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
    unit, source = _primary_price(doc, price, store)
    indicative_only=False
    if unit is None and store=="CHIP7":
        unit=_chip7_financing_pvp(doc,price)
        if unit is not None:
            source="CHIP7 financing PVP — indicative, contact shop"
            indicative_only=True
    if unit is None and store=="Chipman":
        unit=_chipman_tax_price(doc,price)
        if unit is not None:
            source="Chipman primary VAT-inclusive price"
    if unit is None:
        return None, "price_not_found"
    currency = doc.select_one("meta[property='product:price:currency'], meta[itemprop='priceCurrency']")
    if currency and currency.get("content") and currency.get("content").strip().upper() != "EUR":
        return None, "non_eur_price"
    status = _primary_stock(doc, stock)
    if store=="PcComponentes":
        # Retain unknown unless the main product explicitly says unavailable.
        primary_status=_pccomponentes_stock(doc)
        if primary_status=="out_of_stock":
            status="out_of_stock"
    # ON4TECH puts its stock indicator beside the actual primary price.
    # Do not infer "in stock" from recommended product cards.
    if store=="ON4TECH":
        main=doc.select_one("main, #product, .product-detalhe") or doc.body
        primary_text=main.get_text(" ",strip=True)[:2500] if main else ""
        if re.search(r"Produto\s+Esgotado",primary_text,re.I):
            status="out_of_stock"
    if indicative_only:
        status = "unknown"  # An installment example proves neither stock nor checkout price.
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
    if indicative_only:
        item["indicative_only"]=True
    return item, "indicative_price" if indicative_only else "verified_price"
