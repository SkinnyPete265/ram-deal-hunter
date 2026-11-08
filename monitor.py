#!/usr/bin/env python3
"""Conservative personal desktop-DDR4 deal watcher. No bypasses or checkout automation."""
import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from retailer_parser import extract_html_offer, category_card_offers
from browser_render import render_dom
try:
    from curl_cffi import requests as browser_requests
except ImportError:
    browser_requests = None

ROOT = Path(__file__).parent
DATA = Path(os.environ.get("RAM_DEAL_DATA_FILE") or (ROOT / "docs/data.json")).expanduser().resolve()
AGENT = {"User-Agent": "RAMDealHunter/1.0 (personal price research; low frequency)", "Accept-Language": "pt-PT,pt;q=0.9,es;q=0.7"}
HOSTS = {
    "PCDIGA": "pcdiga.com", "PcComponentes": "pccomponentes.pt",
    "Globaldata": "globaldata.pt", "CHIP7": "chip7.pt", "ON4TECH": "on4tech.pt",
    "Novo Atalho": "novoatalho.pt", "Castro Electrónica": "castroelectronica.pt",
    "Chipman": "chipman.pt", "Switch Technology": "switchtechnology.pt",
    "You Get": "youget.pt", "KIBO": "kibo.pt", "El Shop": "elshop.es",
    "PCBox": "pcbox.pt", "Fnac": "fnac.pt",
}
NEG = ("outofstock","soldout","esgotado","sem stock","agotado","indisponivel","indisponível")
POS = ("instock","in stock","em stock","disponivel","disponível","en stock")
FETCH_META = {}
BROWSER_LANGUAGE = "pt-PT,pt;q=0.9,es;q=0.8,en;q=0.5"

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def matches(name):
    s = re.sub(r"\s+","",str(name).lower().replace("×","x").replace("*","x"))
    # Preserve a module-count boundary after DDR4 when the space was removed:
    # "DDR4 2x16GB" must not become "DDR42x16GB" (nor 11x16 become 1x16).
    s = re.sub(r"(?<=ddr4)(?=\d+x)"," ",s)
    # An unambiguous Crucial CP2K16G4/CT2K16G4 DDR4 model can validate
    # listings (e.g. Fnac marketplace) that omit "DDR4" from their headings.
    trusted_ddr4_sku=bool(re.search(r"\b(?:cp|ct)2k16g4[a-z0-9]+\b",str(name).lower()))
    if ("ddr4" not in s and not trusted_ddr4_sku) or "ddr5" in s or any(t in s for t in ("sodimm","so-dimm","laptop","rdimm","lrdimm","eccreg","260pin","registeredmemory","servermemory")):
        return None
    # Kingston KVRxxS... part numbers describe laptop SO-DIMMs even when
    # a seller's title incorrectly calls the module a generic DIMM.
    # E.g. Kingston KVR32S22D8/16 is officially a 260-pin SO-DIMM.
    if re.search(r"kvr\d{2}s\d{2}[a-z0-9]+[/_]\d{1,3}(?!\d)",str(name).lower()):
        return None
    # Crucial CT...G4S... models are laptop SO-DIMMs, not desktop UDIMMs.
    # Example CT16G4SFRA32AT is sold under generic 1x16GB DDR4 headings.
    if re.search(r"\bct\d+g4s[a-z0-9]+\b",str(name).lower()):
        return None
    if any(re.search(p,s) for p in (r"1x32(?:gb)?",r"4x8(?:gb)?",r"2x8(?:gb)?",r"4x4(?:gb)?",r"2x32(?:gb)?",r"4x16(?:gb)?",r"8x4(?:gb)?")):
        return None
    raw=str(name).lower()
    # Manufacturer part numbers can reveal a 16GB *kit of two 8GB sticks*
    # even when the retail title merely says "16 GB DIMM".
    if (re.search(r"\bf4-[a-z0-9]+d-16[a-z0-9]*\b",raw) or
        re.search(r"\bkf4\d{2}[a-z0-9]+k2[/\-]16\b",raw) or
        re.search(r"\bcm[a-z]+16gx4m2[a-z0-9]+\b",raw) or
        re.search(r"\b(?:cp|ct)2k8g4[a-z0-9]+\b",raw) or
        # Patriot 16GB Viper Steel "PVS416G...K" is a kit of 2x8GB,
        # despite shops labelling it generically as a 16GB DIMM.
        re.search(r"\bpvs416g[a-z0-9]+k\b",raw)):
        return None
    if re.search(r"(?<!\d)(?:2x16(?:gb)?|16gbx2)(?!\d)",s):
        return "kit"
    # Retailer descriptions sometimes express the actual kit as
    # "dois módulos de 16 GB" instead of "2x16GB".
    if re.search(r"\b(?:2|dois|duas|two)\s+(?:m[oó]dulos?|modules?|dimms?|sticks?)\s*(?:(?:de|of|com|x)\s*)?16\s*gb\b",
                 str(name).lower(),re.I):
        return "kit"
    # Well-defined matched-kit part-number families (DDR4 only). The suffix
    # identifies the *total* 32GB kit and K2/M2/D the two-module package.
    # A single 32GB stick such as KF432C16BB/32 must not match.
    if (re.search(r"\bkf4\d{2}[a-z0-9]+k2[/\-]32\b",str(name).lower()) or
        re.search(r"\bf4-[a-z0-9]+d-32[a-z0-9]+\b",str(name).lower()) or
        re.search(r"\b(?:cp|ct)2k16g4[a-z0-9]+\b",str(name).lower()) or
        re.search(r"\bcm[a-z]+32gx4m2[a-z0-9]+\b",str(name).lower())):
        return "kit"
    if re.search(r"(?<!\d)(?:1x16(?:gb)?|16gbx1)(?!\d)",s) and "32gb" not in s:
        return "single_pair"
    # A clearly named single 16GB desktop DIMM is also eligible, purchased twice.
    # Never infer this from a kit/pack description or from a laptop/server product.
    if re.search(r"(?<![0-9])16\s*gb(?![0-9])",str(name).lower()) and "32gb" not in s and (
        "dimm" in s or "udimm" in s or "modulo" in s or "module" in s
    ) and not any(w in s for w in ("kit","pack","bundle")) and not re.search(r"\d+x\d+(?:gb)?",s):
        return "single_pair"
    return None

def price(value):
    if value is None: return None
    s = re.sub(r"[^0-9,.]","",str(value))
    if not s: return None
    if "." in s and "," in s: s = s.replace(".","").replace(",",".") if s.rfind(",") > s.rfind(".") else s.replace(",","")
    elif "," in s: s = s.replace(",",".")
    try:
        v = float(s)
        return round(v,2) if 0 < v < 10000 else None
    except ValueError: return None

def stock(value):
    s = str(value).lower().replace("_","")
    if any(x in s for x in NEG): return "out_of_stock"
    if any(x in s for x in POS): return "in_stock"
    return "unknown"

def allowed(store,url):
    p=urlparse(url)
    h=p.hostname or ""
    d=HOSTS.get(store,"")
    return p.scheme=="https" and bool(d) and (h==d or h.endswith("."+d))

def product_info(html,store,url):
    doc=BeautifulSoup(html,"html.parser")
    for el in doc.find_all("script",type="application/ld+json"):
        try: data=json.loads(el.string or el.get_text() or "{}")
        except (ValueError,TypeError): continue
        queue=[data]
        while queue:
            item=queue.pop()
            if isinstance(item,list): queue.extend(item); continue
            if not isinstance(item,dict): continue
            queue.extend(item.get("@graph",[]) if isinstance(item.get("@graph"),list) else [])
            kinds=item.get("@type",[])
            if isinstance(kinds,str): kinds=[kinds]
            if not any(str(k).rstrip("/").split("/")[-1]=="Product" for k in kinds): continue
            name=str(item.get("name") or "")
            properties=item.get("additionalProperty") or []
            if isinstance(properties,dict): properties=[properties]
            extra=" ".join(str(p.get("name",""))+" "+str(p.get("value","")) for p in properties if isinstance(p,dict))
            kind=matches(name) or matches(name+" "+extra)
            # Some sellers omit the module count from the visible title, while
            # their exact product URL contains an unambiguous manufacturer SKU.
            # Use that corroboration only for a title explicitly saying
            # "DDR4 32GB"; never trust arbitrary URL words like "2x16".
            if (not kind and "ddr4" in name.lower() and
                    re.search(r"\b32\s*gb\b",name,re.I) and
                    re.search(r"(?:cm[a-z]+32gx4m2[a-z0-9]+|kf4\d{2}[a-z0-9]+k2[/\-]32|f4-[a-z0-9]+d-32[a-z0-9]+)",url,re.I)):
                kind=matches(name+" "+url)
            if not kind: continue
            offers=item.get("offers") or []
            if isinstance(offers,dict): offers=[offers]
            for o in offers:
                if not isinstance(o,dict) or str(o.get("priceCurrency","EUR")).upper()!="EUR": continue
                unit=price(o.get("price") or o.get("lowPrice"))
                if unit is None: continue
                availability=stock(o.get("availability"))
                # Prefer an explicit primary-product out-of-stock statement on PCBox pages
                # to potentially stale structured availability.
                if store=="PCBox" and re.search(r"produto n[aã]o dispon[ií]vel no momento",html,re.I):
                    availability="out_of_stock"
                if kind=="single_pair" and availability=="in_stock": availability="unknown"
                amount=round(unit*(2 if kind=="single_pair" else 1),2)
                identity=hashlib.sha256((store+":"+url.split("?")[0]).encode()).hexdigest()[:16]
                mhz=re.search(r"\b(2133|2400|2666|2933|3000|3200|3466|3600|3733|4000|4266)\b",name)
                cl=re.search(r"\bCL\s*(\d\d)\b",name,re.I)
                return dict(id=identity,store=store,url=url,title=name,configuration=kind,units_to_buy=2 if kind=="single_pair" else 1,unit_price_eur=unit,price_eur=amount,stock=availability,shipping_to_pt="unverified",speed_mhz=int(mhz[1]) if mhz else None,cas_latency=int(cl[1]) if cl else None,source="Retailer product JSON-LD",observed_at=stamp(),current=True)
    # Retailers such as Chipman and Castro Electrónica expose prices in
    # product-level HTML widgets even when their JSON-LD is absent/incomplete.
    return extract_html_offer(html, store, url, matches, price, stock, stamp)[0]

def _request_with_transient_retry(url):
    """One gentle retry for intermittent 502/503/504 or request timeouts.

    Permanent 403/404/410 failures are not retried here. HTTP fingerprint
    fallback for access-denied responses remains a separate operation.
    """
    for attempt in range(2):
        try:
            response=requests.get(url,headers=AGENT,timeout=18)
        except requests.Timeout:
            if attempt:
                raise
            time.sleep(0.4)
            continue
        if response.status_code in (502,503,504) and attempt==0:
            time.sleep(0.4)
            continue
        return response
    raise RuntimeError("HTTP retry exhausted")


def _castro_transient_fallback(url):
    """Try a separate HTTP transport once after Castro server errors/timeouts.

    Do not reuse cookies or a browser profile. Never turn an error page into
    an offer: normal HTML and product-price verification still apply.
    """
    if browser_requests is None:
        return None
    try:
        response=browser_requests.get(url,impersonate="chrome",
            headers={"Accept-Language":BROWSER_LANGUAGE},timeout=20)
        return response if response.status_code==200 else None
    except Exception:
        return None


def download(url):
    """Request a public product page; retry one blocked request with a browser-like TLS client.

    This does not solve CAPTCHA/JS challenges, authenticate, or use proxy services.
    Unsuccessful attempts remain visible as blocked rather than as product data.
    """
    host=urlparse(url).hostname or ""
    record=FETCH_META.setdefault(host,{"attempted":0,"recovered":0,"still_blocked":0,
        "transient_attempted":0,"transient_recovered":0})
    castro=(host=="castroelectronica.pt" or host.endswith(".castroelectronica.pt"))
    try:
        response=_request_with_transient_retry(url)
    except requests.Timeout:
        if not castro:
            raise
        record["transient_attempted"]+=1
        recovered=_castro_transient_fallback(url)
        if recovered is None:
            raise
        record["transient_recovered"]+=1
        response=recovered
    if castro and response.status_code in (502,503,504):
        record["transient_attempted"]+=1
        recovered=_castro_transient_fallback(url)
        if recovered is not None:
            record["transient_recovered"]+=1
            response=recovered
    if response.status_code in (403,429):
        record["attempted"]+=1
        browser=None
        if browser_requests is not None:
            try:
                browser=browser_requests.get(url,impersonate="chrome",headers={"Accept-Language":BROWSER_LANGUAGE},timeout=20)
            except Exception:
                # Some websites reject both transports. Preserve the original HTTP status.
                browser=None
        if browser is not None and browser.status_code==200:
            record["recovered"]+=1
            response=browser
        else:
            record["still_blocked"]+=1
    response.raise_for_status()
    if "html" not in response.headers.get("Content-Type","").lower() or len(response.content)>5000000:
        raise ValueError("Unsupported response")
    # Some retailers omit a charset header. requests then falls back to
    # Latin-1 and corrupts UTF-8 euro symbols ("€" -> "â\u0082¬"), which
    # prevents our locale-aware price parser from recognizing the amount.
    try:
        body=response.content.decode("utf-8")
    except UnicodeDecodeError:
        body=response.text
    # A successful HTTP response can still be an anti-bot challenge, not a product.
    if re.search(r"<title>\s*(just a moment|attention required|access denied)[^<]*</title>",body,re.I):
        raise ValueError("Browser challenge shown instead of a retailer page")
    return body

def links(html,base,store):
    """Collect candidates; the product page itself must independently prove the configuration."""
    doc=BeautifulSoup(html,"html.parser")
    found=[]
    ddr4_category="ddr4" in base.lower()
    for a in doc.find_all("a",href=True):
        u=urljoin(base,a["href"]).split("?")[0].split("#")[0]
        if not allowed(store,u) or u in found or u.rstrip("/")==base.rstrip("/"):
            continue
        title=a.get_text(" ",strip=True)
        explicit=matches(title+" "+u.replace("-"," "))
        # DDR4-only category pages may omit DDR4 or module counts in link text.
        # Fetch a 16GB/32GB product candidate, then verify its Product JSON-LD.
        category_candidate=ddr4_category and bool(
            re.search(r"(?:16|32)\s*gb",title,re.I) and
            re.search(r"(?:ram|mem[oó]ria|memory|dimm|kit)",title,re.I)
        )
        if explicit or category_candidate:
            found.append(u)
        if len(found)>=25:
            break
    return found

def comparison_offers(html, base, source="KuantoKusta"):
    """Extract *unverified* lowest listed prices from a public PT comparison category.

    These are discovery candidates, never an assertion of store inventory or
    delivered price. Product titles must independently identify DDR4 and 2x16GB.
    """
    doc=BeautifulSoup(html,"html.parser")
    found={}
    for a in doc.select("a[href]"):
        link=urljoin(base,a.get("href","")).split("#")[0]
        parsed=urlparse(link)
        if parsed.scheme!="https" or parsed.hostname not in ("kuantokusta.pt","www.kuantokusta.pt"):
            continue
        if not re.match(r"^/p/\d+/",parsed.path): continue
        raw=a.get_text(" ",strip=True)
        m=re.search(r"(?:desde\s*)?(\d{1,5}(?:[.,]\d{2}))\s*€",raw,re.I)
        if not m: continue
        title=re.split(r"\s+desde\s*\d",raw,maxsplit=1,flags=re.I)[0].strip()
        kind=matches(title)
        if not kind: continue
        unit=price(m.group(1))
        if not unit: continue
        total=round(unit*(2 if kind=="single_pair" else 1),2)
        identity=hashlib.sha256(("comparison:"+link).encode()).hexdigest()[:16]
        mhz=re.search(r"\b(2133|2400|2666|2933|3000|3200|3466|3600|3733|4000|4266)\b",title)
        cl=re.search(r"\bCL\s*(\d\d)\b",title,re.I)
        found[identity]=dict(id=identity,store=source+" comparison",url=link,title=title,
            configuration=kind,units_to_buy=2 if kind=="single_pair" else 1,
            unit_price_eur=unit,price_eur=total,stock="unknown",
            shipping_to_pt="unverified",speed_mhz=int(mhz[1]) if mhz else None,
            cas_latency=int(cl[1]) if cl else None,
            source="Comparison lowest advertised price, merchant/stock/shipping not verified",
            observed_at=stamp(),current=True,comparison_only=True)
    return list(found.values())

def price_diagnostic(html,url):
    """Store a small public-page diagnostic; never store HTML, cookies or form data."""
    doc=BeautifulSoup(html,"html.parser")
    title=doc.select_one("h1")
    output={"url":url.split("?")[0][:180],
            "heading":title.get_text(" ",strip=True)[:140] if title else ""}
    found=[]
    for node in doc.select("[class*='price'],[id*='price'],[itemprop='price']"):
        if node.name in ("script","input","textarea"):continue
        value=node.get("content") or node.get("data-price-amount") or node.get_text(" ",strip=True)
        if not value or len(value)>90 or not re.search(r"(?i)(?:€|EUR|[0-9][.,][0-9]{2})",value):
            continue
        classes=" ".join(node.get("class",[]))[:100]
        item=[node.name,classes,node.get("id","")[:50],str(value)[:80]]
        if item not in found:found.append(item)
        if len(found)>=7:break
    output["price_nodes"]=found
    prices=[]
    for meta in doc.select("meta"):
        key=meta.get("property") or meta.get("name") or meta.get("itemprop") or ""
        if "price" in key.lower():
            prices.append([key[:75],str(meta.get("content",""))[:70]])
        if len(prices)>=6:break
    output["price_meta"]=prices
    return output

def eligible_for_alert(offer,budget):
    """Only direct retailers' available items can trigger a deal notification.

    Stock for two separate single DIMMs remains unverified, even if one is
    listed in stock. Catalogue-only and comparison candidates aren't verified.
    """
    return (offer.get("price_eur",float("inf"))<=budget and
            offer.get("stock")=="in_stock" and
            not offer.get("catalogue_only") and
            not offer.get("comparison_only") and
            not offer.get("indicative_only") and
            offer.get("configuration")=="kit" and
            offer.get("units_to_buy")==1)

def notify(o):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: return False
    msg="DDR4 RAM DEAL CANDIDATE: €%.2f\n%s\n%s\n%s\n" % (o["price_eur"],o["title"],o["store"],o["url"])
    msg+="\nAvailability and shipping to Portugal NOT confirmed; verify at checkout."
    try:
        r=requests.post("https://api.telegram.org/bot"+token+"/sendMessage",json={"chat_id":chat,"text":msg,"disable_web_page_preview":True},timeout=15)
        return r.ok and r.json().get("ok",False)
    except (requests.RequestException,ValueError): return False

def save_snapshot(path, output):
    """Replace the published JSON only after a complete file is written."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    try:
        temporary.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(temporary,path)
    finally:
        if temporary.exists():
            temporary.unlink()

def run():
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    previous=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"offers":[]}
    earlier={o["id"]:o for o in previous.get("offers",[])}
    targets={}
    with (ROOT/"watchlist.csv").open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if allowed(row["store"],row["url"]): targets[(row["store"],row["url"])]=True
    health=[]
    catalogue_offers={}
    FETCH_META.clear()
    blocked_stores=set()
    for store,url in cfg["retailer_pages"]:
        try:
            html=download(url)
            discovered=links(html,url,store)
            for u in discovered: targets[(store,u)]=True
            cards=category_card_offers(html,store,url,matches,price,stock,stamp,allowed)
            for item in cards:
                catalogue_offers[item["id"]]=item
                targets[(store,item["url"])]=True
            health.append({"source":store+" category","status":"ok","found":len(discovered),"priced_cards":len(cards)})
        except (requests.RequestException,ValueError) as e:
            is_blocked=isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code in (403,429)
            if is_blocked: blocked_stores.add(store)
            health.append({"source":store+" category","status":"blocked_403_or_429" if is_blocked else "error","detail":str(e)[:130]})
        time.sleep(0.3)
    # Round-robin stores so one large catalogue cannot crowd out smaller shops.
    grouped={}
    for store,url in targets:
        grouped.setdefault(store,[]).append(url)
    queue=[]
    while any(grouped.values()) and len(queue)<120:
        for store,urls in grouped.items():
            if urls and len(queue)<120: queue.append((store,urls.pop(0)))
    offers=dict(catalogue_offers)
    debug_counts={}
    browser_attempts={}
    for store,url in queue:
        if store in blocked_stores:
            continue
        try:
            html=download(url)
            item=product_info(html,store,url)
            if item:
                offers[item["id"]]=item
            else:
                _,reason=extract_html_offer(html,store,url,matches,price,stock,stamp)
                # Some PcComponentes/CHIP7 purchase boxes are filled by JavaScript.
                # A limited number of *Windows-only* Chrome/Edge DOM renders are
                # attempted after a normal page proved its product identity.
                # Never infer the main item's price from recommendation cards.
                budget={"PcComponentes":6,"CHIP7":3}.get(store,0)
                if (reason=="price_not_found" and os.name=="nt" and
                        browser_attempts.get(store,0)<budget):
                    browser_attempts[store]=browser_attempts.get(store,0)+1
                    rendered=render_dom(url)
                    if rendered:
                        browser_offer=product_info(rendered,store,url)
                        if browser_offer is not None:
                            browser_offer["source"]+=" (headless browser render)"
                            offers[browser_offer["id"]]=browser_offer
                            health.append({"source":store+" browser render","status":"ok","found":1})
                            continue
                    health.append({"source":store+" browser render",
                                   "status":"no_verified_price",
                                   "detail":"Browser rendering did not reveal a verified primary-product price"})
                detail={"source":store+" product","status":reason}
                # Collect useful diagnostics for price failures, without
                # allowing unrelated products to exhaust each store's quota.
                limit={"price_not_found":2,"configuration_unverified":1,
                       "no_primary_product":1}.get(reason,0)
                sample_key=(store,reason)
                if debug_counts.get(sample_key,0)<limit:
                    detail["sample"]=price_diagnostic(html,url)
                    debug_counts[sample_key]=debug_counts.get(sample_key,0)+1
                health.append(detail)
        except (requests.RequestException,ValueError) as e:
            is_blocked=isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code in (403,429)
            if is_blocked: blocked_stores.add(store)
            health.append({"source":store+" product","status":"blocked_403_or_429" if is_blocked else "error","detail":str(e)[:130]})
        time.sleep(0.3)
    # Public price-comparison pages give indirect visibility into shops that
    # deny automated requests; treat all extracted amounts as *candidates*.
    for source,url in cfg.get("comparison_pages",[]):
        if source!="KuantoKusta" or not url.startswith("https://www.kuantokusta.pt/"):
            continue
        try:
            gathered=comparison_offers(download(url),url,source)
            for item in gathered:
                offers[item["id"]]=item
            health.append({"source":source+" comparison","status":"ok","found":len(gathered),
                           "detail":"Lowest advertised prices; seller and delivery not verified"})
        except (requests.RequestException,ValueError) as e:
            health.append({"source":source+" comparison","status":"error","detail":str(e)[:120]})
        time.sleep(0.3)
    for store in sorted(blocked_stores):
        health.append({"source":store,"status":"automated_access_blocked","detail":"Both standard and browser-like requests failed; this store remains a coverage gap."})
    for store,host in HOSTS.items():
        counts={"attempted":0,"recovered":0,"still_blocked":0}
        for actual,record in FETCH_META.items():
            if actual==host or actual.endswith("."+host):
                for key in counts: counts[key]+=record[key]
        if counts["attempted"]:
            health.append({"source":store+" browser fallback","status":"ok" if counts["recovered"] else "blocked",
                           "found":counts["recovered"],"detail":str(counts["attempted"])+" retries"})
        transient=sum(v.get("transient_attempted",0) for h,v in FETCH_META.items()
            if h==host or h.endswith("."+host))
        recovered=sum(v.get("transient_recovered",0) for h,v in FETCH_META.items()
            if h==host or h.endswith("."+host))
        if transient:
            health.append({"source":store+" transient fallback",
                           "status":"ok" if recovered else "failed","found":recovered,
                           "detail":str(transient)+" retries after gateway error/timeout"})
    # No paid API services are used. Only configured retailer pages are scanned.
    # Keep observations only when freshly confirmed. Older entries remain visible but stale.
    for ident,item in offers.items():
        old=earlier.get(ident,{})
        history=old.get("history",[])[-119:]
        if not history or history[-1]["price_eur"]!=item["price_eur"] or history[-1]["stock"]!=item["stock"]:
            history.append({"at":item["observed_at"],"price_eur":item["price_eur"],"stock":item["stock"]})
        item["history"]=history
        alerted=old.get("alerted_price_eur")
        if eligible_for_alert(item,cfg["budget_eur"]) and (alerted is None or item["price_eur"]<=alerted-5):
            if notify(item): alerted=item["price_eur"]
        if not eligible_for_alert(item,cfg["budget_eur"]): alerted=None
        item["alerted_price_eur"]=alerted
    for ident,item in earlier.items():
        if ident not in offers: offers[ident]={**item,"current":False}
    output={"last_scan":stamp(),"budget_eur":cfg["budget_eur"],"offers":sorted(offers.values(),key=lambda x:(not x["current"],x["price_eur"])),"health":health,"note":"Prices observed on retailer pages. Stock and shipping to Portugal must be confirmed at checkout."}
    save_snapshot(DATA,output)
    print("Scan complete:",len(offers),"tracked offers;",len(health),"source checks")

if __name__=="__main__": run()
