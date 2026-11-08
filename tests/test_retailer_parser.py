"""Fixtures model real retailer patterns: PrestaShop primary prices and price tags."""
from monitor import product_info, matches, price, stock, stamp, allowed
from retailer_parser import category_card_offers


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


def test_chipman_price_with_vat_label_without_standard_css():
    html = """
    <html><head><meta name="description" content="Desktop DDR4 32GB (2x16GB)"></head>
    <body><main id="main">
      <h1>G.Skill DDR4 32GB (2x16GB) Ripjaws V</h1>
      <div class="special-offer">
       <span>239,90 €</span> <span>Com IVA</span>
      </div>
      <div class="recommended"><h2>Memory 8GB DDR4</h2><span>19,00 €</span></div>
    </main></body></html>
    """
    o=product_info(html,"Chipman","https://chipman.pt/memorias-ram/gskill-ripjaws")
    assert o and o["price_eur"]==239.9
    assert o["source"].startswith("Chipman primary VAT-inclusive price")


def test_chipman_catalogue_card_price_and_safe_stock():
    html = """
    <section>
      <article class="product-miniature">
        <h2 class="product-title">
          <a href="/memorias-ram/gskill-2x16">Memória RAM G.Skill Aegis DDR4 32GB (2x16GB) 3200MHz CL16</a>
        </h2>
        <div class="product-price-and-shipping">
          <span class="regular-price">299,90 €</span>
          <span class="price">264,90 €</span>
        </div>
        <button>Adicionar ao carrinho</button>
      </article>
      <article class="product-miniature">
        <h2 class="product-title"><a href="/memorias-ram/laptop">
          Memória RAM DDR4 32GB 2x16GB SO-DIMM
        </a></h2>
        <span class="price">29,90 €</span>
      </article>
      <article class="product-miniature">
        <h2 class="product-title"><a href="/memorias-ram/ddr5">
          Memória RAM DDR5 32GB 2x16GB UDIMM
        </a></h2>
        <span class="price">89,90 €</span>
      </article>
    </section>
    """
    base="https://chipman.pt/categorias/memorias-ram-ddr4"
    offers=category_card_offers(html,"Chipman",base,matches,price,stock,stamp,allowed)
    assert len(offers)==1
    o=offers[0]
    assert o["price_eur"]==264.9
    assert o["stock"]=="unknown"
    assert o["catalogue_only"] is True
    assert o["url"]=="https://chipman.pt/memorias-ram/gskill-2x16"


def test_catalogue_card_single_pair_price_doubled():
    html = """
    <article class="product-miniature">
      <h2 class="product-title"><a href="/memorias-ram/apacer16">
        Memória RAM Apacer DDR4 16GB DIMM 3200MHz
      </a></h2>
      <div class="product-price-and-shipping"><span class="price">79,90 €</span></div>
    </article>
    """
    base="https://chipman.pt/categorias/memorias-ram-ddr4"
    offers=category_card_offers(html,"Chipman",base,matches,price,stock,stamp,allowed)
    assert len(offers)==1 and offers[0]["price_eur"]==159.8
    assert offers[0]["units_to_buy"]==2
    assert offers[0]["stock"]=="unknown"


def test_catalogue_card_ignores_untrusted_host_and_missing_price():
    html = """
    <article class="product-miniature">
      <h2 class="product-title"><a href="https://fakechipman.test/ram">
        RAM DDR4 32GB 2x16GB
      </a></h2>
      <span class="price">39,90 €</span>
    </article>
    <article class="product-miniature">
      <h2 class="product-title"><a href="/memorias-ram/unpriced">
        RAM DDR4 32GB 2x16GB
      </a></h2>
      <div class="delivery">Entregue em 3 dias</div>
    </article>
    """
    assert category_card_offers(html,"Chipman","https://chipman.pt/categorias/memorias-ram-ddr4",matches,price,stock,stamp,allowed)==[]


def test_chipman_real_sale_price_classes():
    html = """
    <html><head><meta name="description"
      content="Crucial DDR4 32GB, 2 x 16 GB desktop kit"></head>
    <body><main><h1>Kit Memória RAM CRUCIAL Pro CP2K16G4DFRA32A (3200MHz - 32GB - DIMM)</h1>
      <span class="text-base text-gray-400 line-through">284,90 €</span>
      <span class="text-3xl font-extrabold text-sale-600 dark:text-sale-400">270,66 €</span>
      <div class="recommended"><span class="product-price">79,00 €</span></div>
    </main></body></html>"""
    p=product_info(html,"Chipman","https://chipman.pt/memorias-ram-ddr4/crucial-pro")
    assert p is not None and p["price_eur"]==270.66 and p["stock"]=="unknown"


def test_castro_online_price_takes_priority_over_physical_store():
    html = """
    <html><body><main>
      <h1>Memória RAM Fury Beast 32GB (2x16GB) DDR4-3200 MHz CL16 - KINGSTON</h1>
      <span class="product-store-price">367,50 €</span>
      <span class="product-opportunity-new-price">349,89 €</span>
      <div class="recommendations"><span class="price-web">50,99 €</span></div>
    </main></body></html>"""
    p=product_info(html,"Castro Electrónica","https://www.castroelectronica.pt/pt/product/fury-beast")
    assert p is not None and p["price_eur"]==349.89


def test_on4tech_primary_price_not_related_products():
    html = """
    <html><head><meta name="description" content="Memória Corsair Vengeance DDR4 32GB 2x16GB PC3600 RGB PRO"></head>
    <body><main><h1>on4tech</h1>
      <span class="product-detalhe-price">€183,00</span>
      <div>Produto Esgotado</div>
      <div class="product-wrap">Memória Corsair 1x16GB <div class="product-price">196,00 €</div></div>
    </main></body></html>"""
    p=product_info(html,"ON4TECH","https://www.on4tech.pt/p3-p-487168-memoria-corsair")
    assert p is not None and p["price_eur"]==183.0 and p["stock"]=="out_of_stock"


def test_related_product_only_price_not_accepted():
    html = """
    <html><head><meta name="description" content="Memória Corsair Vengeance DDR4 32GB (2x16GB)"></head>
    <body><main><h1>on4tech</h1>
      <div class="product-wrap"><span class="product-price">196,00 €</span></div>
    </main></body></html>"""
    assert product_info(html,"ON4TECH","https://www.on4tech.pt/p3-p-487168") is None
