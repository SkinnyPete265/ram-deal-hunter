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
