import json
from monitor import matches, price, stock, product_info, allowed, links, comparison_offers

def test_desktop_configuration():
    assert matches("Corsair 32GB DDR4 3200MHz (2x16GB)")=="kit"
    assert matches("Crucial 16GB DDR4 3200MHz (1x16GB)")=="single_pair"
    assert matches("Corsair 32GB DDR4 3200MHz (1x32GB)") is None
    assert matches("Corsair 32GB DDR4 3200MHz (4x8GB)") is None
    assert matches("Corsair 32GB DDR5 3200MHz (2x16GB)") is None
    assert matches("Crucial 2x16GB DDR4 SO-DIMM 3200MHz") is None

def test_price():
    assert price("185,00 €")==185.0
    assert price("199.99")==199.99
    assert price(None) is None

def test_product_jsonld():
    html='<script type="application/ld+json">'+json.dumps({"@type":"Product","name":"Crucial DDR4 3200MHz 32GB (2x16GB) CL16","offers":{"priceCurrency":"EUR","price":"189.95","availability":"https://schema.org/InStock"}})+'</script>'
    p=product_info(html,"Globaldata","https://www.globaldata.pt/test")
    assert p and p["price_eur"]==189.95 and p["stock"]=="in_stock"

def test_single_modules_are_doubled():
    html='<script type="application/ld+json">'+json.dumps({"@type":"Product","name":"Crucial DDR4 3200MHz 16GB (1x16GB)","offers":{"priceCurrency":"EUR","price":"89.95","availability":"https://schema.org/InStock"}})+'</script>'
    p=product_info(html,"Globaldata","https://www.globaldata.pt/test")
    assert p and p["price_eur"]==179.9 and p["stock"]=="unknown" and p["units_to_buy"]==2

def test_new_store_domains_and_https():
    assert allowed("Novo Atalho","https://www.novoatalho.pt/memorias")
    assert allowed("Castro Electrónica","https://www.castroelectronica.pt/pt/loja-virtual/ddr4-1")
    assert allowed("Chipman","https://chipman.pt/categorias/memorias-ram-ddr4")
    assert allowed("Switch Technology","https://switchtechnology.pt/produto/ddr4-2x16gb/")
    assert allowed("You Get","https://youget.pt/pt/ddr4")
    assert allowed("KIBO","https://www.kibo.pt/produto/kit-ddr4/")
    assert allowed("El Shop","https://elshop.es/en/47-ddr4")
    assert not allowed("El Shop","https://elshop.es.evil.example/en/47-ddr4")
    assert not allowed("KIBO","http://www.kibo.pt/produto/ddr4")

def test_ddr4_kit_and_single_title_variations():
    assert matches("Dimm DDR4 Pack 2x 16GB (32GB) TeamGroup CL16") == "kit"
    assert matches("Dimm DDR4 16GB G.Skill CL16 3200Mhz Aegis") == "single_pair"
    assert matches("Kingston 32 GB (2 x 16 GB) DDR4 DIMM") == "kit"
    assert matches("Kit DDR4 16GB 3200 MHz DIMM") is None
    assert matches("DDR4 16GB 2x8GB DIMM") is None
    assert matches("DDR4 UDIMM 64GB 4x16GB") is None
    assert matches("DDR4 SO-DIMM 16GB 1x16GB") is None

def test_category_discovery_checks_product_pages_independently():
    base="https://chipman.pt/categorias/memorias-ram-ddr4"
    html = """
    <a href="/produto/ram-32gb/">Kit Memória RAM 32 GB DIMM</a>
    <a href="/produto/ram-16gb/">Memória RAM 16GB DIMM</a>
    <a href="/produto/ram-8gb/">Memória RAM 8GB DIMM</a>
    <a href="https://evil.example/product/32gb-ddr4-2x16gb">DDR4 2x16GB</a>
    """
    found=links(html,base,"Chipman")
    assert found==["https://chipman.pt/produto/ram-32gb/","https://chipman.pt/produto/ram-16gb/"]
    assert product_info("<html>not structured product data</html>","Chipman",found[0]) is None

def test_structured_properties_and_pcbox_stock():
    product={
        "@type":"https://schema.org/Product",
        "name":"Kingston Fury Beast Kit 32GB DIMM",
        "additionalProperty":[
            {"name":"Memory type","value":"DDR4"},
            {"name":"Module configuration","value":"2 x 16 GB"}
        ],
        "offers":{"@type":"Offer","priceCurrency":"EUR","price":"159.90","availability":"https://schema.org/InStock"}
    }
    html='<script type="application/ld+json">'+json.dumps(product)+'</script>'
    p=product_info(html,"PCBox","https://www.pcbox.pt/product/example")
    assert p and p["price_eur"]==159.9 and p["stock"]=="in_stock"
    p=product_info(html+"<p>Produto não disponível no momento</p>","PCBox","https://www.pcbox.pt/product/example")
    assert p and p["stock"]=="out_of_stock"

def test_browser_fallback_recovers_public_product_html(monkeypatch):
    import monitor
    from types import SimpleNamespace
    from requests import Response
    def response(code, text):
        r=Response()
        r.status_code=code
        r._content=text.encode("utf-8")
        r.headers["Content-Type"]="text/html; charset=utf-8"
        r.url="https://www.pcdiga.com/test"
        return r
    monkeypatch.setattr(monitor.requests,"get",lambda *a,**k:response(403,"Blocked"))
    calls=[]
    def browser_get(url,**kwargs):
        calls.append((url,kwargs))
        return response(200,"<html><title>DDR4 test</title></html>")
    monkeypatch.setattr(monitor,"browser_requests",SimpleNamespace(get=browser_get))
    monitor.FETCH_META.clear()
    assert "DDR4 test" in monitor.download("https://www.pcdiga.com/test")
    assert calls[0][1]["impersonate"]=="chrome"
    assert monitor.FETCH_META["www.pcdiga.com"]["recovered"]==1

def test_browser_fallback_keeps_blocked_failure(monkeypatch):
    import monitor, pytest
    from types import SimpleNamespace
    from requests import Response, HTTPError
    def response(code):
        r=Response()
        r.status_code=code
        r._content=b"Forbidden"
        r.headers["Content-Type"]="text/html"
        r.url="https://chip7.pt/test"
        return r
    monkeypatch.setattr(monitor.requests,"get",lambda *a,**k:response(403))
    monkeypatch.setattr(monitor,"browser_requests",SimpleNamespace(get=lambda *a,**k:response(403)))
    monitor.FETCH_META.clear()
    with pytest.raises(HTTPError):
        monitor.download("https://chip7.pt/test")
    assert monitor.FETCH_META["chip7.pt"]["still_blocked"]==1

def test_comparison_offers_are_unverified():
    html = """
    <a href="/p/78706/corsair-ddr4">
      Memória RAM Corsair 32GB Vengeance LPX (2x 16GB) DDR4 CL16 3200Mhz Black desde 189,50€ em 12 lojas
    </a>
    <a href="/p/78707/sodimm">
      Memória RAM Crucial 32GB SO-DIMM DDR4 3200Mhz (2x16GB) desde 150,00€
    </a>
    <a href="https://evil.example/p/12/fake">
      Memória RAM Corsair DDR4 (2x16GB) desde 10,00€
    </a>
    <a href="/p/78708/one-by-32">
      Memória RAM DDR4 (1x32GB) desde 89,00€
    </a>
    """
    found=comparison_offers(html,"https://www.kuantokusta.pt/c/11/memoria-ram/f/347-8352/32-gb-ddr4")
    assert len(found)==1
    o=found[0]
    assert o["price_eur"]==189.5
    assert o["comparison_only"] is True
    assert o["stock"]=="unknown"
    assert o["shipping_to_pt"]=="unverified"
    assert o["configuration"]=="kit"
    assert o["url"].startswith("https://www.kuantokusta.pt/p/78706/")
