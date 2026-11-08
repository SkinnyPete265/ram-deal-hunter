"""Fixtures model real retailer patterns: PrestaShop primary prices and price tags."""
from monitor import product_info


def test_chipman_current_price_and_delivery_stock():
    html = """
    <html><head>
      <meta name="description" content="Memória RAM Crucial Pro 32GB DDR4 3200MHz (2x16GB). Kit para desktop.">
    </head><body>
      <div id="product">
        <h1>Kit Memória RAM CRUCIAL Pro CP2K16G4DFRA32A (3200 MHz - 32 GB - DIMM)</h1>
        <div class="product-prices">
          <div class="product-discount"><span class="regular-price">284,90 €</span></div>
          <div class="current-price"><span class="price">270,66 €</span></div>
        </div>
        <div id="product-availability">Disponível Online - Verificar Data de Entrega</div>
      </div>
      <div class="recommendation"><span class="price">10,00 €</span></div>
    </body></html>
    """
    o=product_info(html,"Chipman","https://chipman.pt/memorias-ram/crucial-pro-32gb")
    assert o and o["price_eur"]==270.66 and o["configuration"]=="kit"
    assert o["stock"]=="in_stock" and "HTML fallback" in o["source"]


def test_chipman_meta_price_single_module_doubles_and_stock_stays_unknown():
    html = """
    <html><head>
      <meta property="product:price:amount" content="89.90">
      <meta property="product:price:currency" content="EUR">
    </head><body><main>
      <h1>TeamGroup DDR4 16GB (1x16GB) 3200MHz UDIMM</h1>
      <div class="product-prices"><span class="price">119,90 €</span></div>
      <div id="product-availability">Disponível</div>
    </main></body></html>
    """
    o=product_info(html,"Chipman","https://chipman.pt/memorias-ram/teamgroup-16gb")
    assert o and o["price_eur"]==179.8 and o["units_to_buy"]==2
    assert o["stock"]=="unknown" and o["source"].startswith("Product price metadata")


def test_castro_primary_product_price_attribute():
    html = """
    <html><head><meta name="description" content="Kit DDR4 32GB (2x16GB) desktop"></head>
    <body><main><h1>Corsair Vengeance LPX RAM 32GB DDR4 3200MHz</h1>
      <div class="product-info-main"><div class="price-final_price">
        <span class="price-wrapper" data-price-amount="197.45"><span class="price">197,45 €</span></span>
      </div></div>
      <div class="upsell"><span class="price">25,00 €</span></div>
    </main></body></html>
    """
    o=product_info(html,"Castro Electrónica","https://www.castroelectronica.pt/pt/memorias/corsair")
    assert o and o["price_eur"]==197.45


def test_does_not_guess_price_from_recommendations():
    html = """
    <html><head><meta name="description" content="Kit DDR4 32GB 2x16GB para desktop"></head>
    <body><main><h1>Crucial DDR4 32GB (2x16GB)</h1>
      <div class="recommendation"><span class="price">49,99 €</span></div>
    </main></body></html>
    """
    assert product_info(html,"Chipman","https://chipman.pt/memorias-ram/crucial") is None


def test_does_not_accept_laptop_so_dimm():
    html = """
    <html><head><meta property="product:price:amount" content="79.99"></head>
    <body><main><h1>Crucial DDR4 32GB (2x16GB) SO-DIMM Laptop</h1></main></body></html>
    """
    assert product_info(html,"Chipman","https://chipman.pt/memorias-ram/laptop") is None


def test_no_verified_price_without_product_identity():
    html = """<html><head><meta property="product:price:amount" content="5.00"></head>
    <body><h1>Memórias RAM DDR4</h1></body></html>"""
    assert product_info(html,"Chipman","https://chipman.pt/categorias/memorias-ram-ddr4") is None


def test_explicit_non_euro_metadata_rejected():
    html = """
    <html><head>
      <meta property="product:price:amount" content="189.90">
      <meta property="product:price:currency" content="USD">
    </head><body><h1>Crucial 32GB DDR4 (2x16GB)</h1></body></html>
    """
    assert product_info(html,"Chipman","https://chipman.pt/memorias-ram/crucial") is None


def test_preferred_current_price_over_strikethrough_old_price():
    html = """
    <html><body><div id="product">
      <h1>Kingston 32GB DDR4 (2x16GB) UDIMM 3200MHz</h1>
      <div class="product-prices">
        <span class="regular-price">299,00 €</span>
        <div class="current-price">
          <span class="price">194,66 €</span>
        </div>
      </div>
    </div></body></html>
    """
    o=product_info(html,"Chipman","https://chipman.pt/memorias-ram/kingston")
    assert o and o["price_eur"]==194.66
