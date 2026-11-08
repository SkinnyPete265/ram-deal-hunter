"""Optional Amazon.es Keepa connector. Keepa prices are not PT checkout totals."""
import os
import re
import requests
from monitor import matches, price, stamp

def amazon_offers():
    key=os.getenv("KEEPA_API_KEY")
    if not key:
        return [],{"source":"Amazon.es / Keepa","status":"not_configured"}
    products=[]
    errors=[]
    for term in ("DDR4 32GB 2x16GB","DDR4 16GB 1x16GB"):
        try:
            r=requests.get("https://api.keepa.com/search",params={"key":key,"domain":9,"type":"product","term":term,"history":0,"stats":1},timeout=35)
            r.raise_for_status()
            response=r.json()
            if response.get("error"): raise ValueError(str(response["error"])[:120])
            products.extend(response.get("products") or [])
        except (requests.RequestException,ValueError) as e: errors.append(str(e)[:120])
    offers={}
    for p in products:
        asin=p.get("asin","")
        name=p.get("title","")
        kind=matches(name)
        if not kind or not re.fullmatch("[A-Z0-9]{10}",asin): continue
        # current prices are cents. Buy Box price is preferred, then Amazon/new offers.
        stats=p.get("stats") or {}
        current=stats.get("current") or []
        raw=next((current[i] for i in (18,0,1) if len(current)>i and isinstance(current[i],int) and current[i]>0),None)
        if raw is None: continue
        unit=raw/100
        total=round(unit*(2 if kind=="single_pair" else 1),2)
        url="https://www.amazon.es/dp/"+asin
        mhz=re.search(r"\b(2133|2400|2666|2933|3000|3200|3466|3600|3733|4000|4266)\b",name)
        cl=re.search(r"\bCL\s*(\d\d)\b",name,re.I)
        offers[asin]=dict(id="amazon-"+asin,store="Amazon.es",url=url,title=name,configuration=kind,units_to_buy=2 if kind=="single_pair" else 1,unit_price_eur=round(unit,2),price_eur=total,stock="unknown",shipping_to_pt="unverified",speed_mhz=int(mhz[1]) if mhz else None,cas_latency=int(cl[1]) if cl else None,source="Keepa search snapshot; NOT PT checkout",observed_at=stamp(),current=True)
    status="error" if errors else "ok"
    return list(offers.values()),{"source":"Amazon.es / Keepa","status":status,"found":len(offers),"detail":"; ".join(errors)[:150]}
