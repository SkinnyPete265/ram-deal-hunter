/* Merge independent GitHub-cloud and Windows-home scans without overwriting either. */
(function (scope) {
  "use strict";
  // 8-hour scan cadence: allow a delayed run but retire missed updates at 12h.
  const MAX_AGE_MS = 12 * 60 * 60 * 1000;
  function millis(value) {
    const t = Date.parse(value || "");
    return Number.isFinite(t) ? t : 0;
  }
  function mergeSnapshots(cloud, home, now) {
    const currentTime = Number.isFinite(now) ? now : Date.now();
    const sourceList = [
      {label: "GitHub cloud", snapshot: cloud},
      {label: "Home PC", snapshot: home}
    ];
    const bestById = new Map();
    const health = [];
    const timestamps = {};
    const scanTriggers = {};
    const freshness = {};

    for (const source of sourceList) {
      const snap = source.snapshot;
      timestamps[source.label] = snap && snap.last_scan || null;
      // Older snapshots predate scan_trigger; never guess they were scheduled.
      scanTriggers[source.label] = snap && ["manual", "scheduled", "push"].includes(snap.scan_trigger)
        ? snap.scan_trigger : "unknown";
      if (!snap) {
        freshness[source.label] = false;
        continue;
      }
      const scannedAt = millis(snap.last_scan);
      const isFresh = scannedAt > 0 &&
          currentTime >= scannedAt - 2 * 60 * 1000 &&
          currentTime - scannedAt <= MAX_AGE_MS;
      freshness[source.label] = isFresh;

      if (isFresh) {
        for (const check of (snap.health || [])) {
          health.push(Object.assign({}, check, {scan_origin: source.label}));
        }
      }

      for (const raw of (snap.offers || [])) {
        if (!raw || typeof raw.id !== "string" ||
            !Number.isFinite(Number(raw.price_eur))) continue;
        const o = Object.assign({}, raw, {
          scan_origin: source.label,
          current: Boolean(raw.current && isFresh)
        });
        const old = bestById.get(o.id);
        // Prefer a freshly observed offer to stale observations, regardless
        // of which scanner produced the higher timestamp.
        const score = (o.current ? 1e16 : 0) + millis(o.observed_at);
        if (!old || score > old.score) bestById.set(o.id, {offer: o, score: score});
      }
    }

    const offers = Array.from(bestById.values(), x => x.offer)
      .sort((a, b) => Number(b.current) - Number(a.current) || a.price_eur - b.price_eur);
    const times = Object.values(timestamps).map(millis);
    const last = Math.max(0, ...times);
    const latestSource = last
      ? (millis(timestamps["Home PC"]) >= millis(timestamps["GitHub cloud"]) ? "Home PC" : "GitHub cloud")
      : null;
    return {
      budget_eur: Number(cloud && cloud.budget_eur) || Number(home && home.budget_eur) || 200,
      last_scan: last ? new Date(last).toISOString() : null,
      offers: offers,
      health: health,
      sources: {
        cloud_last_scan: timestamps["GitHub cloud"],
        home_last_scan: timestamps["Home PC"],
        cloud_scan_trigger: scanTriggers["GitHub cloud"],
        home_scan_trigger: scanTriggers["Home PC"],
        cloud_is_fresh: freshness["GitHub cloud"],
        home_is_fresh: freshness["Home PC"],
        latest_scan_origin: latestSource,
        latest_scan_trigger: latestSource ? scanTriggers[latestSource] : "unknown",
        latest_is_fresh: latestSource ? freshness[latestSource] : false
      }
    };
  }
  const api = { mergeSnapshots: mergeSnapshots };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  scope.RAMHunterMerge = api;
})(typeof window !== "undefined" ? window : globalThis);
