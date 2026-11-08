const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/index.html', 'utf8');
const inline = Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))
  .map(m => m[1]).filter(x => x.trim());

assert.equal(inline.length, 1, 'Expected one inline dashboard controller script');
new vm.Script(inline[0], {filename: 'docs/index.html inline.js'});

assert(html.includes('browser render'), 'Browser render source must join retailer health');
assert(html.includes('g.render_recovered'), 'Source health must count browser render successes');
assert(html.includes("o.stock==='in_stock'&&!o.comparison_only&&!o.catalogue_only"),
  'Deal count should exclude speculative comparison and catalogue prices');
assert(html.includes("GitHub Actions → Run workflow"), 'Manual scan guidance stays visible');
for (const id of ["scan-home-time", "scan-cloud-time", "scan-home-kind", "scan-cloud-kind"]) {
  assert(html.includes('id="'+id+'"'), 'Missing scan timestamp UI: '+id);
}
assert(html.includes("drawScanInfo()"), 'Dashboard must show provenance after loading both snapshots');
assert(html.includes("scanKind(sources.latest_scan_trigger"), 'Latest scan must identify manual/scheduled origin');
assert(html.includes("timeZone:'Europe/Lisbon'"), 'Timestamps must use Portugal local time');
assert(html.includes("Snapshot outdated"), 'Old data must not appear recently scanned');
assert(html.includes("Indicative credit PVP"), "Indicative CHIP7 prices must be visibly labelled");
assert(html.includes("transient fallback"), "Temporary Castro HTTP recovery must be grouped by store");
console.log('Dashboard inline JS syntax and status checks passed');
