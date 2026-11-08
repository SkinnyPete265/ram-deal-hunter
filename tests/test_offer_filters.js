const assert = require('node:assert/strict');
const F = require('../docs/offer-filters.js');

const kit = {current:true, store:'Globaldata', price_eur:259.90,
  stock:'in_stock', configuration:'kit', units_to_buy:1};
const expensive = {...kit, store:'CHIP7', price_eur:342.90};
const soldOut = {...kit, store:'PcComponentes', price_eur:130.11, stock:'out_of_stock'};
const catalogue = {...kit, store:'Castro', price_eur:170, catalogue_only:true};
const comparison = {...kit, store:'KuantoKusta', price_eur:160, comparison_only:true};
const indicative = {...kit, store:'CHIP7', price_eur:150, indicative_only:true};
const single = {...kit, store:'You Get', price_eur:100, stock:'unknown',
  configuration:'single_pair', units_to_buy:2};
const outdated = {...kit, store:'PCBox', price_eur:90, current:false};

const offers = [kit,expensive,soldOut,catalogue,comparison,indicative,single,outdated];
assert.deepEqual(F.counts(offers,200), {
  all:7, available:2, budget:5, unknown:1, out:1, deals:0
});
assert.equal(F.closestAvailable(offers),kit);
assert.equal(F.matching(soldOut,'budget',200),true,
 'budget-only filtering intentionally includes unavailable listings');
assert.equal(F.matching(comparison,'budget',200),true,
 'comparison candidates must be visibly labelled, not silently removed');
assert.equal(F.matching(catalogue,'available',200),false);
assert.equal(F.matching(comparison,'available',200),false);
assert.equal(F.matching(indicative,'available',200),false);
assert.equal(F.matching(single,'available',200),false);
assert.equal(F.matching(outdated,'available',200),false);
assert.equal(F.closestAvailable([soldOut,catalogue,comparison,indicative,outdated]),null);
assert.equal(F.counts([{...kit,price_eur:199.99}],200).deals,1,
 'shipping must not be inferred or added to product-only budget');
assert.equal(F.counts([{...kit,price_eur:200.01}],200).deals,0);
assert.equal(F.counts([{...kit,price_eur:200}],200).deals,1);
assert.equal(F.counts([{...kit,price_eur:200,shipping_to_pt:'unverified'}],200).deals,1);
assert.equal(F.matching({...kit,stock:'unknown'},'unknown',200),true);
assert.equal(F.matching(soldOut,'out',200),true);
assert.equal(F.matching(kit,'out',200),false);
console.log('Dashboard quick filters, product-only budget and closest offer tests passed');
