import json
from monitor import matches, price, stock, product_info, allowed, links

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
