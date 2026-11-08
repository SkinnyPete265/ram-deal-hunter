/* Pure helpers for sorting genuine retailer availability from speculative prices.
 * Product budget is deliberately EXCLUSIVE of delivery charges.
 */
(function (scope) {
  "use strict";

  const MODES = Object.freeze(["all", "available", "budget", "unknown", "out"]);

  function validPrice(o) {
    return o && Number.isFinite(Number(o.price_eur)) && Number(o.price_eur) > 0;
  }

  function directRetailerPrice(o) {
    return Boolean(o && !o.comparison_only && !o.catalogue_only && !o.indicative_only);
  }

  function listedAvailable(o) {
    // Only an in-stock retail KIT proves that both 16 GB modules are listed.
    // One 16 GB stick in stock is not evidence that two can be purchased.
    return Boolean(o && o.current && validPrice(o) && directRetailerPrice(o) &&
      o.stock === "in_stock" && o.configuration === "kit" && o.units_to_buy === 1);
  }

  function underBudget(o, budget) {
    // This is intentionally JUST the product price; shipping is checked by
    // the buyer at checkout. Budget filter can contain out-of-stock products.
    return Boolean(validPrice(o) && Number(o.price_eur) <= Number(budget));
  }

  function matching(o, mode, budget) {
    switch (mode) {
      case "available": return listedAvailable(o);
      case "budget": return underBudget(o, budget);
      case "unknown": return o.stock === "unknown";
      case "out": return o.stock === "out_of_stock";
      default: return true;
    }
  }

  function counts(offers, budget) {
    const current = (offers || []).filter(o => o && o.current);
    const result = {};
    for (const mode of MODES)
      result[mode] = current.filter(o => matching(o, mode, budget)).length;
    result.deals = current.filter(o => listedAvailable(o) && underBudget(o, budget)).length;
    return result;
  }

  function closestAvailable(offers) {
    // A comparison price or finance PVP cannot be the "closest buyable" offer.
    return (offers || []).filter(listedAvailable)
      .sort((a,b) => Number(a.price_eur) - Number(b.price_eur))[0] || null;
  }

  const api = {MODES, listedAvailable, directRetailerPrice, underBudget,
    matching, counts, closestAvailable};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  scope.RAMHunterFilters = api;
})(typeof window !== "undefined" ? window : globalThis);
