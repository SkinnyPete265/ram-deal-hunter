const assert = require('node:assert/strict');
const { mergeSnapshots } = require('../docs/merge.js');

const now = Date.parse('2026-11-08T12:00:00Z');
const t = x => new Date(now - x * 60000).toISOString();

const cloud = {
  budget_eur: 200, last_scan: t(20),
  offers: [
    {id: 'a', title: 'PCDIGA', price_eur: 180, observed_at: t(20), current: false},
    {id: 'b', title: 'Globaldata', price_eur: 265, observed_at: t(20), current: true}
  ],
  health: [{source: 'PCDIGA category', status: 'blocked_403_or_429'}]
};
const home = {
  budget_eur: 200, last_scan: t(5),
  offers: [
    {id: 'a', title: 'PCDIGA', price_eur: 175, observed_at: t(5), current: true},
    {id: 'c', title: 'PCBox', price_eur: 91, observed_at: t(5), current: true, stock: 'out_of_stock'}
  ],
  health: [{source: 'PCDIGA category', status: 'ok'}]
};
const merged = mergeSnapshots(cloud, home, now);
assert.equal(merged.last_scan, t(5));
assert.equal(merged.offers.length, 3);
assert.equal(merged.offers.find(o => o.id === 'a').price_eur, 175);
assert.equal(merged.offers.find(o => o.id === 'a').scan_origin, 'Home PC');
assert.equal(merged.offers.find(o => o.id === 'b').scan_origin, 'GitHub cloud');
assert(merged.health.some(h => h.scan_origin === 'Home PC' && h.status === 'ok'));
assert(merged.health.some(h => h.scan_origin === 'GitHub cloud' && h.status === 'blocked_403_or_429'));

const noHome = mergeSnapshots(cloud, null, now);
assert.equal(noHome.offers.length, 2);
assert.equal(noHome.sources.home_last_scan, null);

// An eight-hour scan must remain usable until the next scheduled run.
const betweenScans = mergeSnapshots(cloud, home, now + 9 * 60 * 60 * 1000);
assert.equal(betweenScans.offers.filter(o => o.current).length, 2);
assert(betweenScans.health.length > 0);

// A missed update must eventually become stale rather than advertised as live.
const late = mergeSnapshots(cloud, home, now + 13 * 60 * 60 * 1000);
assert(late.offers.every(o => !o.current));
assert.equal(late.health.length, 0);

const duplicates = mergeSnapshots(
  {last_scan: t(10), offers: [{id: 'x', price_eur: 100, observed_at: t(10), current: true}]},
  {last_scan: t(5), offers: [{id: 'x', price_eur: 90, observed_at: t(5), current: true}]},
  now
);
assert.equal(duplicates.offers.length, 1);
assert.equal(duplicates.offers[0].price_eur, 90);
console.log('Home/cloud dashboard merge tests passed');
