"""Safety regression tests for bounded Windows stock-only browser checks."""
from monitor import compatible_browser_stock, browser_stock_reason
from browser_render import _ALLOWED_HOSTS


def offer(**changes):
    result = {
        "store": "PcComponentes",
        "configuration": "kit",
        "title": "Kingston FURY Beast RGB 32GB DDR4 3200MHz 2x16GB",
        "price_eur": 185.0,
        "stock": "unknown",
    }
    result.update(changes)
    return result


def test_rendered_availability_can_enrich_matching_kit_only():
    assert compatible_browser_stock(offer(), offer(stock="out_of_stock"))
    assert compatible_browser_stock(offer(), offer(stock="in_stock"))


def test_rendered_availability_never_overrides_unrelated_or_ambiguous_product():
    assert not compatible_browser_stock(offer(), offer(stock="unknown"))
    assert not compatible_browser_stock(offer(), offer(stock="in_stock", price_eur=75))
    assert not compatible_browser_stock(offer(), offer(stock="in_stock", configuration="single_pair"))
    assert not compatible_browser_stock(offer(), offer(stock="in_stock", store="PCDIGA"))
    assert not compatible_browser_stock(offer(), offer(
        stock="in_stock", title="Corsair Vengeance LPX 32GB DDR4 3200MHz 2x16GB"))
    assert not compatible_browser_stock(offer(configuration="single_pair"),
                                        offer(stock="in_stock"))
    assert not compatible_browser_stock(offer(), None)


def test_browser_hosts_are_explicitly_limited_to_supported_retailers():
    assert {"pccomponentes.pt", "chip7.pt", "pcdiga.com",
            "chipman.pt", "castroelectronica.pt"}.issubset(set(_ALLOWED_HOSTS))
    assert "amazon.es" not in _ALLOWED_HOSTS


def test_browser_stock_diagnostics_are_specific_and_do_not_expose_html():
    original=offer()
    assert browser_stock_reason(original, None, False)=="browser_render_unavailable"
    assert browser_stock_reason(original, None)=="rendered_product_or_price_unreadable"
    assert browser_stock_reason(original, offer(stock="unknown"))=="rendered_stock_unverified"
    assert browser_stock_reason(original, offer(price_eur=199,stock="in_stock"))=="rendered_price_mismatch"
    assert browser_stock_reason(original, offer(store="CHIP7",stock="in_stock"))=="rendered_product_mismatch"
    assert browser_stock_reason(original, offer(title="Different DDR4 kit",stock="in_stock"))=="rendered_identity_unverified"


def test_stock_only_render_can_detect_unavailable_main_pccomponentes_kit():
    from retailer_parser import browser_stock_only
    from monitor import stock
    html="""<html><body><main>
      <h1>Kingston FURY Beast RGB 32GB DDR4 3200MHz 2x16GB</h1>
      <p>Disponibilidade do produto Sem data exacta de chegada</p>
    </main></body></html>"""
    result, reason=browser_stock_only(html,"PcComponentes",offer()["title"],stock)
    assert (result,reason)==("out_of_stock","explicit_main_stock")


def test_stock_only_render_rejects_recommendations_and_mismatched_identity():
    from retailer_parser import browser_stock_only
    from monitor import stock
    html="""<html><body><main>
      <h1>Kingston FURY Beast RGB 32GB DDR4 3200MHz 2x16GB</h1>
      <button>Adicionar ao carrinho</button>
      <div class="related-products"><span class="product-availability">Esgotado</span>
       <p>Disponibilidade do produto Sem data exacta de chegada</p></div>
    </main></body></html>"""
    result,reason=browser_stock_only(html,"PcComponentes",offer()["title"],stock)
    assert result=="unknown"
    result,reason=browser_stock_only(html,"PcComponentes",
                                      "Corsair Vengeance LPX DDR4 3200MHz 2x16GB",stock)
    assert (result,reason)==("unknown","rendered_heading_mismatch")


def test_stock_only_render_requires_explicit_availability_and_not_cart_button():
    from retailer_parser import browser_stock_only
    from monitor import stock
    html="""<html><body><main>
      <h1>Kingston FURY Beast RGB 32GB DDR4 3200MHz 2x16GB</h1>
      <button>Adicionar ao carrinho</button>
    </main></body></html>"""
    result,_=browser_stock_only(html,"PcComponentes",offer()["title"],stock)
    assert result=="unknown"


def test_stock_only_chipman_rejects_recommendation_stock():
    from retailer_parser import browser_stock_only
    from monitor import stock
    title=offer()["title"]
    html=f"""<html><body><main><h1>{title}</h1>
      <div class="recommendations"><span class="product-availability">Disponível</span></div>
    </main></body></html>"""
    assert browser_stock_only(html,"Chipman",title,stock)[0]=="unknown"
    html=f"""<html><body><main><h1>{title}</h1>
      <span class="product-availability">Esgotado</span>
    </main></body></html>"""
    assert browser_stock_only(html,"Chipman",title,stock)[0]=="out_of_stock"


def test_browser_stock_distinguishes_access_challenge_from_product_mismatch():
    from retailer_parser import browser_stock_only
    from monitor import stock
    challenge="""<html><head><title>Just a moment...</title></head>
    <body><main><h1>Checking your browser</h1></main></body></html>"""
    assert browser_stock_only(challenge,"PcComponentes",offer()["title"],stock)==(
        "unknown","rendered_access_challenge")
    normal="""<html><body><main><h1>Different DDR4 kit, 2x16GB</h1></main>
    </body></html>"""
    assert browser_stock_only(normal,"PcComponentes",offer()["title"],stock)==(
        "unknown","rendered_heading_mismatch")
