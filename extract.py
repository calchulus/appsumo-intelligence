"""Extract all products from an AppSumo browse category via the esbrowse API.

Usage: python3 extract.py <group> <category> [subcategory]
"""
import json, subprocess, sys, csv
from urllib.parse import quote

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
API = "https://appsumo.com/api/v2/deals/esbrowse/"


def fetch(params):
    qs = "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in params.items())
    url = f"{API}?{qs}"
    r = subprocess.run(
        ["curl", "-sS", "-m", "60", "-A", UA,
         "-H", "Accept: application/json",
         "-H", f"Referer: https://appsumo.com/{'/'.join(SLUGS)}/",
         url],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"curl failed ({r.returncode}): {r.stderr[:200]}")
    return json.loads(r.stdout)


SLUGS = sys.argv[1:4] or ["operations", "productivity-automation"]

base = {
    "include_aggs": "true",
    "status": "current",
    "sort": "recommended",
    "per_page": "20",
    "attribute[group]": SLUGS[0],
    "attribute[category]": SLUGS[1],
}
if len(SLUGS) > 2:
    base["attribute[subcategory]"] = SLUGS[2]

deals, page, total, total_pages = [], 1, None, None
while True:
    d = fetch({**base, "page": str(page)})
    m = d["meta"]
    total, total_pages = m["total_results"], m["total_pages"]
    deals += d["deals"]
    print(f"  page {page}/{total_pages}: +{len(d['deals'])} (running {len(deals)})", file=sys.stderr)
    if page >= total_pages or not d["deals"]:
        break
    page += 1

# de-dupe by id, preserve API order
seen, out = set(), []
for d in deals:
    if d["id"] in seen:
        continue
    seen.add(d["id"])
    out.append(d)

assert len(out) == total, f"got {len(out)} deals but meta says {total}"

rows = []
for i, d in enumerate(out, 1):
    attrs = d.get("attributes") or {}
    rev = d.get("deal_review") or {}
    dates = d.get("dates") or {}
    price, orig = d.get("price"), d.get("original_price")
    off = round((1 - price / orig) * 100) if price and orig and orig > price else None
    kind = "Marketplace" if d.get("is_marketplace") else ("Labs" if d.get("is_labs") else "AppSumo Select")
    plans = ", ".join(p[0] for p in (d.get("unique_plan_types") or []) if p and p[0]) or None
    rows.append({
        "#": i,
        "name": d.get("public_name"),
        "slug": d.get("slug"),
        "url": "https://appsumo.com" + (d.get("get_absolute_url") or ""),
        "tagline": (d.get("card_description") or "").strip(),
        "price_usd": price,
        "original_price_usd": orig,
        "discount_pct": off,
        "plus_price_usd": d.get("plus_discount_price"),
        "is_free": d.get("is_free"),
        "rating": rev.get("average_rating"),
        "reviews": rev.get("review_count"),
        "plan_types": plans,
        "listing": kind,
        "deal_status": d.get("browse_deal_status"),
        "subcategory": ", ".join(attrs.get("subcategory") or []) or None,
        "alternative_to": ", ".join(attrs.get("alternative_to") or []) or None,
        "features": ", ".join(attrs.get("features") or []) or None,
        "start_date": (dates.get("start_date") or "")[:10] or None,
        "end_date": (dates.get("end_date") or "")[:10] or None,
        "review_summary": (d.get("reviews_summary") or "").strip(),
    })

stem = "-".join(SLUGS)
json.dump({"source_url": f"https://appsumo.com/{'/'.join(SLUGS)}/",
           "api": API, "total_results": total, "count": len(rows), "products": rows},
          open(f"{stem}.json", "w"), indent=1, ensure_ascii=False)
with open(f"{stem}.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

print(f"\nTOTAL {len(rows)}/{total} -> {stem}.json, {stem}.csv", file=sys.stderr)
for r in rows:
    pr = "FREE" if r["is_free"] else f"${r['price_usd']:g}"
    rt = f"{r['rating']}* ({r['reviews']})" if r["rating"] else "no reviews"
    print(f"{r['#']:>2}. {r['name']:<38} {pr:>7}  {rt:<16} {r['listing']}")
