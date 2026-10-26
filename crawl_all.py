"""Crawl every AppSumo browse category via the esbrowse API.

Taxonomy comes from /api/dealattribute/personal/ (group -> category dependencies).
Writes per-category JSON/CSV plus a de-duplicated master product list.
"""
import csv, json, os, sys, time
import concurrent.futures as cf
from urllib.parse import quote

import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "categories")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
API = "https://appsumo.com/api/v2/deals/esbrowse/"
PER_PAGE = 250
WORKERS = 4

GROUP_NAMES = {}
PAIRS = []  # (group, category, category_name)


def load_taxonomy():
    a = {x["slug"]: x for x in json.load(open(os.path.join(HERE, "attrs.json")))}
    for g in a["group"]["type_options"]["options"]:
        GROUP_NAMES[g["value"]] = g["name"]
    for c in a["category"]["type_options"]["options"]:
        for g in (c.get("dependency") or {}).get("group") or []:
            PAIRS.append((g, c["value"], c["name"]))


def fetch(params, tries=4):
    qs = "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in params.items())
    url = f"{API}?{qs}"
    last = None
    for t in range(tries):
        r = subprocess.run(
            ["curl", "-sS", "-m", "60", "-A", UA,
             "-H", "Accept: application/json",
             "-H", "Referer: https://appsumo.com/browse/", url],
            capture_output=True, text=True)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError as e:
                last = f"bad json: {e}: {r.stdout[:120]}"
        else:
            last = f"curl rc={r.returncode}: {r.stderr[:150]}"
        time.sleep(1.5 * (t + 1))
    raise RuntimeError(f"gave up after {tries} tries: {last}")


def crawl_category(pair):
    group, cat, cat_name = pair
    base = {
        "status": "current", "sort": "recommended", "per_page": str(PER_PAGE),
        "attribute[group]": group, "attribute[category]": cat,
    }
    deals, page, total, pages = [], 1, None, None
    while True:
        d = fetch({**base, "page": str(page)})
        m = d["meta"]
        total, pages = m["total_results"], m["total_pages"]
        deals += d["deals"]
        if page >= pages or not d["deals"]:
            break
        page += 1

    seen, uniq = set(), []
    for x in deals:
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        uniq.append(x)

    # every returned deal must self-report this taxonomy
    mism = [x["slug"] for x in uniq
            if ((x.get("taxonomy") or {}).get("group") or {}).get("value_enumeration") != group
            or ((x.get("taxonomy") or {}).get("category") or {}).get("value_enumeration") != cat]

    return {"group": group, "group_name": GROUP_NAMES.get(group, group),
            "category": cat, "category_name": cat_name,
            "url": f"https://appsumo.com/{group}/{cat}/",
            "total_results": total, "fetched": len(uniq), "taxonomy_mismatches": mism,
            "deals": uniq}


def rowify(d, rank=None):
    attrs = d.get("attributes") or {}
    rev = d.get("deal_review") or {}
    dates = d.get("dates") or {}
    price, orig = d.get("price"), d.get("original_price")
    off = round((1 - price / orig) * 100) if price and orig and orig > price else None
    kind = ("Marketplace" if d.get("is_marketplace")
            else "Labs" if d.get("is_labs") else "AppSumo Select")
    plans = ", ".join(p[0] for p in (d.get("unique_plan_types") or []) if p and p[0]) or None
    return {
        "rank_in_category": rank,
        "deal_id": d.get("id"),
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
        "group": ", ".join(attrs.get("group") or []) or None,
        "category": ", ".join(attrs.get("category") or []) or None,
        "subcategory": ", ".join(attrs.get("subcategory") or []) or None,
        "alternative_to": ", ".join(attrs.get("alternative_to") or []) or None,
        "best_for": ", ".join(attrs.get("best_for") or []) or None,
        "features": ", ".join(attrs.get("features") or []) or None,
        "start_date": (dates.get("start_date") or "")[:10] or None,
        "end_date": (dates.get("end_date") or "")[:10] or None,
        "review_summary": (d.get("reviews_summary") or "").strip(),
    }


def crawl_uncategorized():
    """Site-wide current deals whose taxonomy is empty -> they appear in no browse category.

    Also gives us the authoritative site-wide total to reconcile category coverage against.
    """
    deals, page, total, pages = [], 1, None, None
    while True:
        d = fetch({"status": "current", "sort": "recommended",
                   "per_page": str(PER_PAGE), "page": str(page)})
        m = d["meta"]
        total, pages = m["total_results"], m["total_pages"]
        deals += d["deals"]
        if page >= pages or not d["deals"]:
            break
        page += 1
    seen, uniq = set(), []
    for x in deals:
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        uniq.append(x)
    orphan = [x for x in uniq if not (x.get("taxonomy") or {})]
    return {"site_wide_total": total, "site_wide_unique": len(uniq),
            "uncategorized": orphan}


def main():
    load_taxonomy()
    print(f"{len(PAIRS)} categories to crawl across {len(GROUP_NAMES)} groups", file=sys.stderr)
    results, errors = [], []
    site = {"site_wide_total": None, "site_wide_unique": None, "uncategorized": []}
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(crawl_category, p): p for p in PAIRS}
        futs[ex.submit(crawl_uncategorized)] = None
        for f in cf.as_completed(futs):
            p = futs[f]
            try:
                r = f.result()
                if p is None:
                    site = r
                    print(f"  site-wide current deals: {r['site_wide_unique']}/{r['site_wide_total']}"
                          f" ({len(r['uncategorized'])} uncategorized)", file=sys.stderr, flush=True)
                    continue
                results.append(r)
                flag = " !!MISMATCH" if r["taxonomy_mismatches"] else ""
                print(f"  {r['group_name']} > {r['category_name']}: "
                      f"{r['fetched']}/{r['total_results']}{flag}", file=sys.stderr, flush=True)
            except Exception as e:
                errors.append((p, str(e)[:200]))
                print(f"  ERROR {p}: {str(e)[:200]}", file=sys.stderr, flush=True)
            # checkpoint after every category
            json.dump(results, open(os.path.join(HERE, "_raw_checkpoint.json"), "w"))

    results.sort(key=lambda r: (list(GROUP_NAMES).index(r["group"]), r["category"]))

    # per-category files
    summary = []
    for r in results:
        stem = f"{r['group']}--{r['category']}"
        rows = [rowify(d, i) for i, d in enumerate(r["deals"], 1)]
        json.dump({k: v for k, v in r.items() if k != "deals"} | {"products": rows},
                  open(os.path.join(OUT, stem + ".json"), "w"), indent=1, ensure_ascii=False)
        if rows:
            with open(os.path.join(OUT, stem + ".csv"), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)
        summary.append({"group": r["group_name"], "category": r["category_name"],
                        "url": r["url"], "products": r["total_results"],
                        "fetched": r["fetched"],
                        "mismatches": len(r["taxonomy_mismatches"])})

    # master de-dupe by deal_id; a product may sit in several categories
    master, cats_of = {}, {}
    for r in results:
        label = f"{r['group_name']} > {r['category_name']}"
        for i, d in enumerate(r["deals"], 1):
            cats_of.setdefault(d["id"], []).append(label)
            if d["id"] not in master:
                master[d["id"]] = rowify(d, i)
    for i, d in enumerate(site["uncategorized"], 1):
        cats_of.setdefault(d["id"], []).append("(uncategorized)")
        if d["id"] not in master:
            master[d["id"]] = rowify(d, i)
    for did, row in master.items():
        row["categories"] = " | ".join(cats_of[did])
        row["category_count"] = len(cats_of[did])

    mrows = sorted(master.values(), key=lambda x: (x["group"] or "~uncategorized",
                                                   x["category"] or "", -(x["reviews"] or 0)))

    cat_sum = sum(r["total_results"] for r in results)
    in_cats = len({d["id"] for r in results for d in r["deals"]})
    coverage = {"site_wide_current_deals": site["site_wide_total"],
                "sum_of_category_counts": cat_sum,
                "unique_products_in_categories": in_cats,
                "unique_products_in_master": len(mrows),
                "uncategorized_deals": len(site["uncategorized"]),
                "duplicate_across_categories": cat_sum - in_cats,
                "taxonomy_mismatches": sum(len(r["taxonomy_mismatches"]) for r in results),
                "errors": len(errors)}
    # every site-wide current deal must be accounted for: in a category, or uncategorized
    coverage["fully_reconciled"] = (
        coverage["unique_products_in_master"] == site["site_wide_total"]
        and coverage["taxonomy_mismatches"] == 0 and not errors)

    json.dump({"source": "https://appsumo.com/browse/", "api": API,
               "categories_crawled": len(results), "errors": errors,
               "coverage": coverage, "category_summary": summary,
               "unique_products": len(mrows), "products": mrows},
              open(os.path.join(HERE, "appsumo_all_products.json"), "w"),
              indent=1, ensure_ascii=False)
    with open(os.path.join(HERE, "appsumo_all_products.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mrows[0].keys()))
        w.writeheader(); w.writerows(mrows)
    with open(os.path.join(HERE, "appsumo_categories_summary.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

    print(f"\nDONE categories={len(results)} errors={len(errors)} "
          f"unique_products={len(mrows)}", file=sys.stderr)
    print("COVERAGE " + json.dumps(coverage), file=sys.stderr)
    for e in errors:
        print("  ERR", e, file=sys.stderr)


main()
