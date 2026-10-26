#!/usr/bin/env python3
"""Campaign economics: what the best AppSumo campaigns actually sold, grossed, and on what terms.

Reads analysis.json + pages.jsonl -> writes campaign_highlights.json.

WHY THIS IS NOT JUST `est_revenue_at_entry`
-------------------------------------------
`sold_estimate` counts LICENSE CODES, not purchases: 418 of the 1,057 tiers grant >1 code per
purchase (up to 10), across 104 products. So `codes x entry_price` is only correct when the ladder is
LINEAR — i.e. price scales exactly with codes, making price-per-code constant. For a linear ladder a
buyer who pays $495 for 5 codes contributes 5 x $99, which is what the floor formula already assumes.
For a PROGRESSIVE ladder price-per-code rises with tier, so the entry-price floor understates.

This script therefore computes price-per-code at every tier and reports a range:
  rev_floor   = codes x min(price/code) over tiers
  rev_ceiling = codes x max(price/code) over tiers
  rev_point   = rev_floor when the ladder is linear (per-code price constant -> the range collapses
                and the number is exact up to the codes-vs-purchases caveat), else the midpoint.

WHAT THESE NUMBERS ARE NOT
--------------------------
* GROSS marketplace revenue, i.e. what buyers paid. AppSumo's revenue split with vendors is not in
  this dataset and is not published per-deal, so vendor net is NOT derivable. Do not call it profit.
* A floor-to-ceiling range, not a measurement: per-tier sales mix is not exposed by the API.
* Only available for products that publish inventory. 174 use codes, 35 are freebie downloads, and
  133 publish nothing and are excluded rather than proxied.
"""
import json, os, re, collections, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = datetime.date(2026, 10, 26)     # the crawl date; all durations are "as of" this
OUT = os.path.join(ROOT, "campaign_highlights.json")

REDEMPTION = re.compile(r"(?:activate|redeem|redemption)[^.]{0,60}?(\d+)\s*day", re.I)
NEW_USER_ONLY = re.compile(r"brand[- ]new [^.]{0,30}users?|only for (?:brand[- ])?new users|"
                           r"no previous accounts|new (?:customers|users) only", re.I)
TRANSFER = re.compile(r"transfer\w* to the new plan|plan name[^.]{0,40}changes", re.I)
STACKABLE = re.compile(r"stack\w*", re.I)


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except Exception:
        return None


def load_plans():
    """slug -> list of (tier, price, codes, public_name, terms[])"""
    out = {}
    with open(os.path.join(ROOT, "pages.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            slug = r.get("slug")
            plans = []
            for p in (r.get("plans") or []):
                try:
                    price = float(p.get("price") or 0)
                except (TypeError, ValueError):
                    price = 0.0
                plans.append({
                    "tier": p.get("tier"), "price": price, "codes": int(p.get("codes") or 0),
                    "name": p.get("public_name") or "", "is_plus": bool(p.get("is_plus_tier")),
                    "highlight": bool(p.get("highlight")),
                    "terms": [t.get("term", "") for t in (p.get("terms") or [])
                              if isinstance(t, dict) and t.get("term")],
                })
            plans.sort(key=lambda x: (x["tier"] is None, x["tier"] or 0))
            out[slug] = plans
    return out


def per_code_prices(plans):
    """Price per license code at each tier that grants codes."""
    out = []
    for p in plans:
        if p["price"] > 0 and p["codes"] > 0:
            out.append(p["price"] / p["codes"])
    return out


def classify_ladder(pcs):
    if len(pcs) < 2:
        return "single-tier", None
    lo, hi = min(pcs), max(pcs)
    if hi == 0:
        return "single-tier", None
    spread = hi / lo
    if spread <= 1.001:
        return "linear", 1.0
    return "progressive", round(spread, 2)


def terms_scan(plans, plan_terms):
    """Pull the contractual terms that actually differ between campaigns."""
    blob = " ".join(t for p in plans for t in p["terms"]) + " " + " ".join(plan_terms or [])
    red = REDEMPTION.search(blob)
    return {
        "redemption_window_days": int(red.group(1)) if red else None,
        "new_users_only": bool(NEW_USER_ONLY.search(blob)),
        "plan_name_transfers": bool(TRANSFER.search(blob)),
        "stacking_mentioned": bool(STACKABLE.search(blob)),
    }


def main():
    d = json.load(open(os.path.join(ROOT, "analysis.json"), encoding="utf-8"))
    plans_by_slug = load_plans()
    prods = d["products"]

    # ---- terms are a campaign property, independent of whether inventory is published ----
    # Measured across ALL 342, not just the 174 with units, otherwise the sample is biased toward
    # code-fulfilled products and understates how standard these clauses are.
    terms_all = collections.Counter()
    refund_hist = collections.Counter()
    redemption_hist = collections.Counter()
    for p in prods:
        t = terms_scan(plans_by_slug.get(p.get("slug"), []), p.get("plan_terms"))
        for k, v in t.items():
            if v not in (None, False):
                terms_all[k] += 1
        refund_hist[p.get("refundable_days")] += 1
        if t["redemption_window_days"]:
            redemption_hist[t["redemption_window_days"]] += 1

    # ---- ladder shape: price-per-code vs the price-based shape already in analysis.json ----
    shape_xtab = collections.Counter()
    for p in prods:
        plans = plans_by_slug.get(p.get("slug"), [])
        pcs = per_code_prices(plans)
        mine, _ = classify_ladder(pcs)
        shape_xtab[(p.get("ladder_shape"), mine)] += 1

    camps = []
    skipped = collections.Counter()
    for p in prods:
        slug = p.get("slug")
        method = p.get("sales_method")
        units = p.get("sold_estimate") or 0
        if method not in ("codes", "downloads"):
            skipped["no inventory published"] += 1
            continue
        if units <= 0:
            skipped["zero units"] += 1
            continue
        plans = plans_by_slug.get(slug, [])
        pcs = per_code_prices(plans)
        shape, spread = classify_ladder(pcs)

        entry = p.get("entry_price") or p.get("price_usd") or (plans[0]["price"] if plans else 0)
        top = p.get("top_price") or (plans[-1]["price"] if plans else None)

        if method == "downloads":
            # 29 of the 35 are $0 lead magnets; the other 6 are cheap paid downloads.
            # Revenue is 0 or trivial - these are distribution, not campaigns. Do not require a price.
            unit_price = float(entry or 0)
            rev_floor = rev_ceiling = rev_point = units * unit_price
            rev_basis = ("free lead magnet ($0)" if unit_price == 0
                         else "downloads x price (single price point)")
        elif pcs:
            rev_floor = units * min(pcs)
            rev_ceiling = units * max(pcs)
            rev_point = rev_floor if shape == "linear" else (rev_floor + rev_ceiling) / 2
            rev_basis = ("exact (linear in price-per-code)" if shape == "linear"
                         else "midpoint of floor/ceiling (price-per-code rises with tier)")
        elif entry:
            rev_floor = rev_ceiling = rev_point = units * float(entry)
            rev_basis = "units x entry price (no per-tier data)"
        else:
            skipped["no price"] += 1
            continue

        start = parse_date(p.get("start_date"))
        end = parse_date(p.get("end_date"))
        # end_date is populated for only 58/342 and is often a 2050 sentinel meaning "no end"
        live = end is None or end > SNAPSHOT or end.year >= 2040
        days = (SNAPSHOT - start).days if start else None
        if days is not None and days <= 0:
            days = 1

        t = terms_scan(plans, p.get("plan_terms"))
        camps.append({
            "slug": slug, "name": p.get("name"), "deal_id": p.get("deal_id"),
            "url": p.get("url") or p.get("product_url"),
            "group": p.get("group"), "category": p.get("category"),
            "listing": p.get("listing"), "plan_types": p.get("plan_types"),
            "units": units, "units_basis": method,
            "entry_price": entry, "top_price": top,
            "tier_count": p.get("tier_count") or len(plans),
            "ladder_shape": shape, "per_code_spread": spread,
            "max_codes_per_purchase": max([q["codes"] for q in plans], default=None),
            "rev_floor": round(rev_floor), "rev_ceiling": round(rev_ceiling),
            "rev_point": round(rev_point), "rev_basis": rev_basis,
            "start_date": p.get("start_date"), "end_date": p.get("end_date"),
            "still_live": live, "days_live": days,
            "units_per_day": round(units / days, 2) if days else None,
            "rev_per_day": round(rev_point / days, 2) if days else None,
            "discount_pct": p.get("discount_pct"), "original_price_usd": p.get("original_price_usd"),
            "wtp_ratio": p.get("wtp_ratio"),
            "refundable_days": p.get("refundable_days"),
            "rating": p.get("rating"), "review_count": p.get("review_count"),
            "stars": p.get("stars"),
            **t,
        })

    # ---- aggregate ----
    paid = [c for c in camps if c["units_basis"] == "codes"]
    free = [c for c in camps if c["units_basis"] == "downloads"]
    lin = [c for c in paid if c["ladder_shape"] == "linear"]
    prog = [c for c in paid if c["ladder_shape"] == "progressive"]

    agg = {
        "snapshot": str(SNAPSHOT),
        "campaigns_with_units": len(camps),
        "paid_campaigns": len(paid),
        "freebie_campaigns": len(free),
        "freebies_at_zero": sum(1 for c in free if c["rev_point"] == 0),
        "excluded": dict(skipped),
        "total_units_paid": sum(c["units"] for c in paid),
        "total_units_free": sum(c["units"] for c in free),
        "gross_rev_floor": sum(c["rev_floor"] for c in paid),
        "gross_rev_ceiling": sum(c["rev_ceiling"] for c in paid),
        "gross_rev_point": sum(c["rev_point"] for c in paid),
        "linear_campaigns": len(lin),
        "progressive_campaigns": len(prog),
        "median_days_live": sorted(c["days_live"] for c in paid if c["days_live"])[len(paid) // 2]
        if paid else None,
        "still_live": sum(1 for c in camps if c["still_live"]),
        "multi_code_tiers": sum(1 for c in paid if (c["max_codes_per_purchase"] or 0) > 1),
    }
    terms = {
        "measured_over": len(prods),
        "refund_window_days": {str(k): v for k, v in refund_hist.most_common()},
        "redemption_window_days": {str(k): v for k, v in redemption_hist.most_common()},
        "clause_prevalence": dict(terms_all.most_common()),
        "ladder_shape_crosstab": {
            f"price-shape={a or 'none'} / per-code-shape={b}": v
            for (a, b), v in sorted(shape_xtab.items(), key=lambda x: -x[1])
        },
    }

    by_rev = sorted(paid, key=lambda c: -c["rev_point"])
    by_vel = sorted([c for c in paid if c["rev_per_day"]], key=lambda c: -c["rev_per_day"])
    by_units = sorted(paid, key=lambda c: -c["units"])
    by_free = sorted(free, key=lambda c: -c["units"])

    out = {
        "method": {
            "units": "sold_estimate = active_codes - codes_remaining (validated against "
                     "freebie_downloads_total: median error 0.3%). Counts LICENSE CODES, not "
                     "purchases - 418/1057 tiers grant >1 code.",
            "revenue": "gross marketplace revenue (what buyers paid), NOT vendor net. AppSumo's "
                       "split is not in this dataset. rev_floor/ceiling span min/max price-per-code "
                       "across tiers; rev_point is exact for linear ladders, else the midpoint.",
            "duration": "start_date -> 2026-10-26 snapshot. end_date is populated for only 58/342 "
                        "and is often a 2050 sentinel, so live campaigns are measured to the snapshot.",
            "coverage": f"{len(camps)} of {len(prods)} products publish inventory; "
                        f"{skipped.get('no inventory published', 0)} publish nothing and are "
                        "excluded rather than proxied.",
        },
        "aggregate": agg,
        "terms": terms,
        "top_by_revenue": by_rev[:25],
        "top_by_velocity": by_vel[:25],
        "top_by_units": by_units[:25],
        "top_freebies": by_free[:10],
        "campaigns": camps,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- console summary ----
    print(f"wrote {OUT}")
    print(f"\ncampaigns with units: {len(camps)} ({len(paid)} paid, {len(free)} freebie); "
          f"excluded: {dict(skipped)}")
    print(f"paid units (lifetime codes): {agg['total_units_paid']:,}")
    print(f"gross revenue  floor ${agg['gross_rev_floor']:,.0f}  "
          f"point ${agg['gross_rev_point']:,.0f}  ceiling ${agg['gross_rev_ceiling']:,.0f}")
    print(f"ladders (price-per-code): {len(lin)} linear (revenue exact) / "
          f"{len(prog)} rising / rest single-tier")
    print(f"median campaign age: {agg['median_days_live']} days; still live: {agg['still_live']}")
    print(f"\nTERMS across all {terms['measured_over']} products:")
    print(f"  refund window (days): {terms['refund_window_days']}")
    print(f"  code-redemption window (days): {terms['redemption_window_days']}")
    print(f"  clause prevalence: {terms['clause_prevalence']}")
    print(f"  ladder shape crosstab (price-based vs per-code):")
    for k, v in terms["ladder_shape_crosstab"].items():
        print(f"     {v:4d}  {k}")
    print("\nTOP 15 BY GROSS REVENUE (point estimate)")
    print(f"{'rev':>12} {'range':>22} {'codes':>8} {'$/day':>8} {'days':>5} {'lad':<11} "
          f"{'refund':>6} {'name'}")
    for c in by_rev[:15]:
        rng = f"${c['rev_floor']/1000:.0f}-{c['rev_ceiling']/1000:.0f}k"
        print(f"${c['rev_point']/1000:>10.0f}k {rng:>22} {c['units']:>8,} "
              f"{c['rev_per_day'] or 0:>8.0f} {c['days_live'] or 0:>5} "
              f"{c['ladder_shape']:<11} {str(c['refundable_days']):>6} {c['name'][:34]}")
    print("\nTOP 10 BY VELOCITY ($/day)")
    for c in by_vel[:10]:
        print(f"  ${c['rev_per_day']:>8,.0f}/day  {c['units']:>7,} codes in {c['days_live']:>4}d  "
              f"{c['name'][:38]}")


if __name__ == "__main__":
    main()
