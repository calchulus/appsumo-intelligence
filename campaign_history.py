"""Step 8: campaign PARTICIPATION history -> campaign_participation.json

Complementary to campaigns.py (which does campaign ECONOMICS: revenue per license code,
velocity, contractual terms). This one uses the `participation` field -- the list of every
promotional campaign slug each product appeared in -- to answer: does being promoted more
actually help, and what does the seasonal campaign calendar look like?

CENTRAL METHODOLOGICAL POINT: campaign depth correlates with units sold, but that is largely
a TENURE artifact -- older products have simply been alive for more sales events. Every
headline is therefore also computed WITHIN launch cohort (earliest campaign year) to
separate "promoted more" from "has been here longer".
"""
import json, os, re, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))

KINDS = [
    ("dotd", "DOTD (deal of the day)", lambda c: "dotd" in c),
    ("last_call", "Last call", lambda c: "last_call" in c or "last-call" in c),
    ("bf", "Black Friday", lambda c: "black" in c and "friday" in c),
    ("sumo", "Sumo Days", lambda c: "sumo_day" in c or "sumo-day" in c),
    ("taco", "Taco Day", lambda c: "taco" in c),
    ("val", "Valentine's", lambda c: "valentines" in c),
    ("plus", "Plus-exclusive", lambda c: "plus" in c),
    ("week", "Themed week", lambda c: "week" in c),
    ("collection", "Curated collection",
     lambda c: any(w in c for w in ("collection", "stack", "essentials"))),
    ("bundle", "Bundle", lambda c: "bundle" in c),
    ("promo", "Site-wide promo",
     lambda c: bool(re.search(r"(spend-get|10-off|15-off|percent|new-\d|off-\d|monthly1k|"
                              r"graduates|drops|monster|build-different|deal-is-right|"
                              r"limited-time)", c))),
]


def kind_of(c):
    cl = c.lower()
    for k, lab, f in KINDS:
        if f(cl):
            return k, lab
    return "other", "Vendor-specific / other"


def year_of(c):
    m = re.search(r"20(\d\d)", c)
    return 2000 + int(m.group(1)) if m else None


def med(v):
    v = [x for x in v if x is not None]
    return round(st.median(v), 1) if v else None


def main():
    det = {d["id"]: d for d in (json.loads(l) for l in open(os.path.join(HERE, "details.jsonl")))}
    A = json.load(open(os.path.join(HERE, "analysis.json")))
    P = {p["deal_id"]: p for p in A["products"]}
    X = {r["deal_id"]: r for r in json.load(open(os.path.join(HERE, "promise_crossref.json")))["rows"]}

    def camps(did):
        return det.get(did, {}).get("participation") or []

    def first_year(did):
        ys = [y for y in (year_of(c) for c in camps(did)) if y]
        return min(ys) if ys else None

    def units_of(p):
        return p["sold_estimate"] if p.get("sales_method") == "codes" else None

    # ---------- campaign inventory
    slots, prods_in, years_seen = collections.Counter(), collections.defaultdict(set), collections.defaultdict(set)
    for did in P:
        for c in camps(did):
            slots[c] += 1
            prods_in[c].add(did)
            y = year_of(c)
            if y:
                years_seen[c].add(y)
    kinds, kind_prods, kind_labels = collections.Counter(), collections.defaultdict(set), {}
    for c, n in slots.items():
        k, lab = kind_of(c)
        kinds[k] += n
        kind_prods[k] |= prods_in[c]
        kind_labels[k] = lab
    kind_rows = [{"k": k, "label": kind_labels[k], "slots": n,
                  "products": len(kind_prods[k]),
                  "distinct": sum(1 for c in slots if kind_of(c)[0] == k)}
                 for k, n in kinds.most_common()]
    top_campaigns = [{"slug": c, "products": len(prods_in[c]), "kind": kind_of(c)[1],
                      "years": sorted(years_seen[c])} for c, _ in slots.most_common(24)]

    # ---------- GA (general access) vs EA (extended access) audiences
    ga = {d for d in P if any(c.lower().endswith(("-ga", "_ga")) for c in camps(d))}
    ea = {d for d in P if any(c.lower().endswith("-ea") or "extended_access" in c.lower() for c in camps(d))}

    # ---------- participation depth vs outcome
    bands = [(0, 0, "0"), (1, 1, "1"), (2, 5, "2-5"), (6, 15, "6-15"), (16, 23, "16-23"), (24, 99, "24+")]
    depth = []
    for lo, hi, lab in bands:
        g = [P[d] for d in P if lo <= len(camps(d)) <= hi]
        if not g:
            continue
        depth.append({"band": lab, "n": len(g),
                      "med_units": med([units_of(p) for p in g]),
                      "med_sat": med([p["fulfillment"]["satisfaction_rate"] for p in g]),
                      "med_rating": med([p["rating"] for p in g]),
                      "med_reviews": med([p["review_count"] or 0 for p in g]),
                      "pct_free": round(sum(1 for p in g if p["is_free"]) * 100 / len(g))})

    # ---------- TENURE CONTROL: split each launch cohort at its own median depth
    cohorts = collections.defaultdict(list)
    for did, p in P.items():
        y = first_year(did)
        if y:
            cohorts[y].append(p)
    tenure = []
    for y in sorted(cohorts):
        g = cohorts[y]
        depths = [len(camps(p["deal_id"])) for p in g]
        m = st.median(depths)
        lo = [p for p in g if len(camps(p["deal_id"])) <= m]
        hi = [p for p in g if len(camps(p["deal_id"])) > m]
        tenure.append({"year": y, "n": len(g), "med_camps": int(m),
                       "med_units": med([units_of(p) for p in g]),
                       "med_sat": med([p["fulfillment"]["satisfaction_rate"] for p in g]),
                       "med_reviews": med([p["review_count"] or 0 for p in g]),
                       "lo_n": len(lo), "lo_units": med([units_of(p) for p in lo]),
                       "lo_sat": med([p["fulfillment"]["satisfaction_rate"] for p in lo]),
                       "hi_n": len(hi), "hi_units": med([units_of(p) for p in hi]),
                       "hi_sat": med([p["fulfillment"]["satisfaction_rate"] for p in hi]),
                       # does the satisfaction gap hold within this cohort?
                       "sat_gap": (round(med([p["fulfillment"]["satisfaction_rate"] for p in lo])
                                         - med([p["fulfillment"]["satisfaction_rate"] for p in hi]), 1)
                                   if lo and hi else None)})

    # ---------- complaint mix by promotion depth
    dd = {d: dict((t["theme"], t["n"]) for t in P[d]["pain_themes"]) for d in P}
    complaint_mix = []
    for lo, hi, lab in [(0, 5, "0-5 campaigns"), (6, 15, "6-15"), (16, 23, "16-23"), (24, 99, "24+ (always-on)")]:
        g = [d for d in P if lo <= len(camps(d)) <= hi]
        neg = sum(P[d]["neg_reviews_analyzed"] for d in g)
        if not neg:
            continue
        complaint_mix.append({"band": lab, "n": len(g), "neg": neg,
                              **{t: round(sum(dd[d].get(t, 0) for d in g) * 100 / neg, 1)
                                 for t in ("deal_devalued", "refund_friction", "feature_gap", "broken")}})

    # ---------- always-on roster (in >=24 recurring campaigns)
    always = []
    for did, p in P.items():
        n = len(camps(did))
        if n < 24:
            continue
        always.append({"name": p["name"], "slug": p["slug"], "url": p["url"], "campaigns": n,
                       "units": p["sold_estimate"], "sales_method": p["sales_method"],
                       "entry_price": p["entry_price"], "is_free": p["is_free"],
                       "satisfaction": p["fulfillment"]["satisfaction_rate"],
                       "reviews": p["review_count"], "category": p["category"],
                       "contradicted": (X.get(did) or {}).get("n_contradicted_claims", 0)})
    always.sort(key=lambda r: -(r["units"] or -1))

    # ---------- recent launch cohort
    recent = [p for did, p in P.items() if (first_year(did) or 0) >= 2025]
    rc = [p for p in recent if p["sales_method"] == "codes" and p["sold_estimate"]]
    recent_rows = sorted(
        ({"name": p["name"], "slug": p["slug"], "url": p["url"], "category": p["category"],
          "units": p["sold_estimate"], "sales_method": p["sales_method"],
          "entry_price": p["entry_price"], "satisfaction": p["fulfillment"]["satisfaction_rate"],
          "reviews": p["review_count"], "campaigns": len(camps(p["deal_id"])),
          "first_year": first_year(p["deal_id"]), "listing": p["listing"],
          "explicit_delivers": p["fulfillment"]["explicit_delivers"],
          "contradicted": (X.get(p["deal_id"]) or {}).get("n_contradicted_claims", 0)}
         for p in recent), key=lambda r: -(r["units"] or -1))

    out = {
        "campaigns_total": len(slots),
        "products_with_history": sum(1 for d in P if camps(d)),
        "year_range": [min((y for c in slots for y in [year_of(c)] if y), default=None),
                       max((y for c in slots for y in [year_of(c)] if y), default=None)],
        "kind_rows": kind_rows, "top_campaigns": top_campaigns,
        "ga_ea": {"both": len(ga & ea), "ga_only": len(ga - ea), "ea_only": len(ea - ga)},
        "depth": depth, "tenure": tenure, "complaint_mix": complaint_mix,
        "always_on": always,
        "recent": {"n": len(recent), "rows": recent_rows[:20], "with_codes": len(rc),
                   "med_units": med([units_of(p) for p in rc]),
                   "max_units": max((units_of(p) for p in rc), default=None),
                   "med_entry": med([p["entry_price"] for p in recent]),
                   "med_sat": med([p["fulfillment"]["satisfaction_rate"] for p in recent]),
                   "contradicted": sum(1 for p in recent if X.get(p["deal_id"]))},
        "history": {str(did): {"campaigns": camps(did), "n": len(camps(did)),
                               "first_year": first_year(did),
                               "kinds": sorted({kind_of(c)[1] for c in camps(did)})}
                    for did in P},
    }
    json.dump(out, open(os.path.join(HERE, "campaign_participation.json"), "w"),
              indent=1, ensure_ascii=False)

    print(f"campaigns: {len(slots)} distinct across {out['year_range']}, "
          f"{out['products_with_history']}/342 products have history")
    print(f"GA/EA: {out['ga_ea']}")
    print(f"always-on roster: {len(always)} | recent (2025-26) cohort: {len(recent)}")
    print(f"\n{'depth':<8}{'n':>5}{'med units':>11}{'med sat':>9}")
    for d in out["depth"]:
        print(f"{d['band']:<8}{d['n']:>5}{(d['med_units'] or 0):>11,.0f}{(d['med_sat'] or 0):>9.1f}")
    print(f"\nTENURE CONTROL (within launch cohort):")
    print(f"{'cohort':<8}{'n':>5}{'lo units':>10}{'hi units':>10}{'lo sat':>8}{'hi sat':>8}{'sat gap':>9}")
    for t in out["tenure"]:
        print(f"{t['year']:<8}{t['n']:>5}{(t['lo_units'] or 0):>10,.0f}{(t['hi_units'] or 0):>10,.0f}"
              f"{(t['lo_sat'] or 0):>8.1f}{(t['hi_sat'] or 0):>8.1f}{(t['sat_gap'] or 0):>9.1f}")
    print(f"cohorts where high-promotion satisfaction is LOWER: "
          f"{sum(1 for t in out['tenure'] if (t['sat_gap'] or 0) > 0)}/{len(out['tenure'])}")
    print(f"\nCOMPLAINT MIX by depth (% of that band's negative reviews):")
    for c in out["complaint_mix"]:
        print(f"  {c['band']:<18} n={c['n']:>3} neg={c['neg']:>5}  deal_devalued={c['deal_devalued']:>4}%  "
              f"refund={c['refund_friction']:>4}%  feature_gap={c['feature_gap']:>4}%")
    print(f"\nwrote campaign_participation.json "
          f"({os.path.getsize(os.path.join(HERE,'campaign_participation.json'))//1024} KB)")


if __name__ == "__main__":
    main()
