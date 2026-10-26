"""Step 1: fetch per-product structured detail from /api/v2/deals/<id>/.

Keeps the feature x tier matrix, full plan/tier ladder, plan terms, rating
breakdown and stock/codes fields. Checkpoints after every product so a partial
run is never lost.
"""
import json, os, subprocess, sys, time
import concurrent.futures as cf
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
OUT = os.path.join(HERE, "details.jsonl")
WORKERS = 6

KEEP = ["id", "slug", "public_name", "availability", "product_url", "refundable_days",
        "plan_stack_count", "codes_remaining", "uses_codes", "uses_limited_licensing",
        "shows_codes_remaining", "freebie_downloads_total", "percent_claimed",
        "plans", "default_plan", "default_plan_terms", "dealfeatures", "core_features",
        "common_features", "features", "addon_features", "deal_review", "deal_comment",
        "participation", "is_marketplace", "is_labs", "browse_deal_status", "is_addon",
        "addon_parent_slug", "stage_details", "unique_plan_types", "use_new_pricing_table"]


def fetch_detail(deal_id, tries=4):
    url = f"https://appsumo.com/api/v2/deals/{deal_id}/"
    last = None
    for t in range(tries):
        r = subprocess.run(["curl", "-sS", "-m", "45", "-A", UA,
                            "-H", "Accept: application/json",
                            "-H", "Referer: https://appsumo.com/browse/", url],
                           capture_output=True, text=True)
        if r.returncode == 0:
            try:
                j = json.loads(r.stdout)
                d = j.get("deal") if isinstance(j, dict) else None
                if d:
                    return {k: d.get(k) for k in KEEP if k in d}
                last = f"no 'deal' key: {list(j)[:6]}"
            except json.JSONDecodeError as e:
                last = f"bad json: {e}"
        else:
            last = f"curl rc={r.returncode} {r.stderr[:120]}"
        time.sleep(1.2 * (t + 1))
    raise RuntimeError(f"id={deal_id}: {last}")


def main():
    master = json.load(open(os.path.join(HERE, "appsumo_all_products.json")))
    targets = [(p["deal_id"], p["name"], p["slug"]) for p in master["products"]]
    print(f"fetching detail for {len(targets)} products", file=sys.stderr)

    done = {}
    if os.path.exists(OUT):  # resume
        for line in open(OUT):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    done[r["id"]] = True
                except Exception:
                    pass
        print(f"resuming: {len(done)} already on disk", file=sys.stderr)

    todo = [t for t in targets if t[0] not in done]
    errors, ok = [], 0
    with open(OUT, "a") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch_detail, t[0]): t for t in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            t = futs[f]
            try:
                rec = f.result()
                # guard against the slug-ignored trap: verify identity by id AND slug
                if rec.get("slug") and t[2] and rec["slug"] != t[2]:
                    errors.append((t[0], f"slug mismatch: want {t[2]} got {rec['slug']}"))
                    continue
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                ok += 1
            except Exception as e:
                errors.append((t[0], str(e)[:160]))
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} (ok={ok} err={len(errors)})", file=sys.stderr, flush=True)

    total = sum(1 for _ in open(OUT))
    print(f"\nDONE ok_this_run={ok} errors={len(errors)} records_on_disk={total}/{len(targets)}",
          file=sys.stderr)
    for e in errors[:15]:
        print("  ERR", e, file=sys.stderr)
    json.dump(errors, open(os.path.join(HERE, "detail_errors.json"), "w"), indent=1)


main()
