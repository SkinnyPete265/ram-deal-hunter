import json
from monitor import matches, price, stock, product_info

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
