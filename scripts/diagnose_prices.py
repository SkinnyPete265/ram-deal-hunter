#!/usr/bin/env python3
"""Public retailer diagnostics: only print limited price-related markup and metadata.

Run from GitHub Actions; never save HTML or credentials to the public repository.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from bs4 import BeautifulSoup
from monitor import ROOT, allowed, download, links, product_info
from retailer_parser import extract_html_offer, _name_and_metadata
from monitor import matches, price, stock, stamp

GROUPS = {"Chipman","Castro Electrónica","Novo Atalho","El Shop","PCBox","KIBO","Globaldata",
          "ON4TECH","Fnac","PCDIGA","PcComponentes","CHIP7","You Get","Switch Technology"}
PRICES = re.compile(r"\d{1,5}[.,]\d{2}\s*(?:€|EUR)|(?:€|EUR)\s*\d{1,5}",re.I)

def summarize(html,store,url,kind):
    doc=BeautifulSoup(html,"html.parser")
    name,details=_name_and_metadata(doc)
    product=product_info(html,store,url) if kind=="product" else None
    secondary,reason=extract_html_offer(html,store,url,matches,price,stock,stamp) if kind=="product" else (None,"category")
    main=doc.select_one("main") or doc.select_one("#main") or doc.select_one("#product") or doc.body
    texts=main.get_text(" ",strip=True) if main else ""
    snippets=[]
    for m in PRICES.finditer(texts):
        part=texts[max(0,m.start()-60):min(len(texts),m.end()+60)]
        if part not in snippets:
            snippets.append(part[:165])
        if len(snippets)>=5:break
    metas=[]
    for tag in doc.select("meta"):
        attr=(tag.get("property") or tag.get("name") or tag.get("itemprop") or "")
        if any(q in attr.lower() for q in ("price","currency","product","description")):
            val=tag.get("content","")
            metas.append([attr,str(val)[:110]])
        if len(metas)>=8:break
    priced_nodes=[]
    for node in doc.find_all(["span","div","p","strong"]):
        if len(node.contents)>4:continue
        value=node.get_text(" ",strip=True)
        if len(value)>100 or not PRICES.search(value):continue
        cls=" ".join(node.get("class") or [])
        ident=node.get("id") or ""
        priced_nodes.append([node.name,cls[:100],ident[:60],value[:100]])
        if len(priced_nodes)>=10:break
    product_types=[]
    for tag in doc.find_all("script",type="application/ld+json"):
        try:
            parsed=json.loads(tag.string or tag.get_text() or "{}")
            preview=str(parsed)[:100]
            product_types.append(preview)
        except Exception: product_types.append("invalid JSON-LD")
        if len(product_types)>=2:break
    if kind=="category" and store in ("Chipman","Castro Electrónica","Novo Atalho","El Shop"):
        cards=[]
        for item in doc.select("article")[:25]:
            title=item.get_text(" ",strip=True)[:110]
            if store=="Chipman" and not re.search(r"32\s*GB|CP2K16|32GIS|32GVK",title,re.I):
                continue
            prices=[]
            for q in item.select("[class*='price'],[class*='sale']"):
                z=q.get_text(" ",strip=True)
                if len(z)<35 and PRICES.search(z):
                    prices.append([" ".join(q.get("class",[]))[:60],z])
                if len(prices)>=3:break
            anchors=[a for a in item.select("a[href]") if a.get("href","").startswith("/")]
            cards.append({"class":" ".join(item.get("class",[]))[:100],
                          "text":title,"links":[[a.get_text(" ",strip=True)[:65],a.get("href","")[:100]] for a in anchors[:2]],
                          "prices":prices[:3]})
            if len(cards)>=4:break
        if store in ("Novo Atalho","El Shop","PCBox"):
            matches_links=[]
            for anchor in doc.select("a[href]"):
                href=anchor.get("href","")
                label=anchor.get_text(" ",strip=True)
                if (re.search(r"ddr4|memori|dimm",label+" "+href,re.I) and
                        (re.search(r"(?:16|32)\\s*GB|2x16",label+" "+href,re.I) or "product" in href)):
                    matches_links.append([label[:125],href[:155]])
                if len(matches_links)>=5:break
            price_trails=[]
            for price_node in doc.select("[class*='price'],[itemprop='price']"):
                value=price_node.get_text(" ",strip=True)
                if len(value)>70 or not PRICES.search(value):continue
                parent=price_node
                trail=[]
                for j in range(6):
                    if not parent or not getattr(parent,"name",None):break
                    as_=parent.select("a[href]")
                    trail.append([parent.name," ".join(parent.get("class",[]))[:70],
                                  len(as_),as_[0].get("href","")[:100] if as_ else ""])
                    if len(as_)>3:break
                    parent=parent.parent
                price_trails.append({"value":value[:60],"trail":trail})
                if len(price_trails)>=2:break
            cards.append({"links":matches_links,"price_trails":price_trails})
        if store=="Castro Electrónica":
            for price_node in doc.select("span.price-web")[:2]:
                ancestor=price_node
                trail=[]
                for j in range(5):
                    if not ancestor or not getattr(ancestor,"name",None):break
                    trail.append([ancestor.name," ".join(ancestor.get("class",[]))[:80],
                        len(ancestor.select("a[href]"))])
                    ancestor=ancestor.parent
                cards.append({"price_ancestor_trail":trail})
        print(json.dumps({"store":store,"kind":"card_diagnostics","cards":cards},ensure_ascii=False))
    print(json.dumps({
        "store":store,"kind":kind,"url":url[:190],
        "h1":name[:220],"matches":matches(details),"metadata_excerpt":details[:350],
        "extraction":reason,"found":bool(product),"price":product.get("price_eur") if product else None,
        "meta":metas,"price_nodes":priced_nodes,"price_snippets":snippets,
        "ld":product_types,
    },ensure_ascii=False))

def main():
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    seen=defaultdict(list)
    with (ROOT/"watchlist.csv").open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if row["store"] in GROUPS and allowed(row["store"],row["url"]):
                seen[row["store"]].append(row["url"])
    for store,url in cfg["retailer_pages"]:
        if store not in GROUPS:continue
        try:
            html=download(url)
            urls=links(html,url,store)
            # Use discovered first, and watchlist links for one-off product samples.
            seen[store]=list(dict.fromkeys(seen[store]+urls))
            print(json.dumps({"store":store,"kind":"category","url":url,"products_found":len(urls),
                              "cards":len(BeautifulSoup(html,"html.parser").select("article, .product-card, .product-miniature"))},ensure_ascii=False))
            if store in ("Chipman","Castro Electrónica"):
                summarize(html,store,url,"category")
        except Exception as e:
            print(json.dumps({"store":store,"kind":"category","error":str(e)[:170]}))
    for store,urls in seen.items():
        max_samples=3 if store in ("Chipman","Castro Electrónica") else 1
        for url in urls[:max_samples]:
            try: summarize(download(url),store,url,"product")
            except Exception as e:
                print(json.dumps({"store":store,"kind":"product","url":url[:140],"error":str(e)[:150]}))

if __name__=="__main__":
    main()
