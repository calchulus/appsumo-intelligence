"""Step 3b: fetch positive review text (rating=4 and rating=5) for all products.

The API caps every rating bucket at 20 records, so for the 165 products with >20
five-star reviews this is a SAMPLE (the 20 most recent), not the full set. Expected
yield: ~1,182 of 1,498 four-star (79%) and ~4,635 of 20,510 five-star (23%).
"""
import json, os, subprocess, sys, time
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
OUT = os.path.join(HERE, "positive.jsonl")
WORKERS = 6
# NOTE: reviewer identity is deliberately NOT captured. See strip_pii.py and README.
KEEP = ["id", "created", "title", "comment", "rating", "up_votes", "down_votes",
        "incentivized", "purchased", "level", "parent_id", "approved"]


def slim(c):
    if not isinstance(c, dict):
        return None
    o = {k: c.get(k) for k in KEEP if c.get(k) is not None}
    return o


def get(url, referer, tries=4):
    last = None
    for t in range(tries):
        r = subprocess.run(["curl", "-sS", "-m", "45", "-A", UA,
                            "-H", "Accept: application/json",
                            "-H", f"Referer: {referer}", url],
                           capture_output=True, text=True)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError as e:
                last = f"bad json {e}"
        else:
            last = f"curl rc={r.returncode} {r.stderr[:100]}"
        time.sleep(1.0 * (t + 1))
    raise RuntimeError(last)


def crawl_one(rec):
    did, slug = rec["id"], rec["slug"]
    ref = f"https://appsumo.com/products/{slug}/"
    base = f"https://appsumo.com/api/v2/deals/{did}"
    dr = rec.get("deal_review") or {}
    out = {"deal_id": did, "slug": slug, "public_name": rec.get("public_name"),
           "buckets": {}, "capped": []}
    for k in (4, 5):
        n = int(dr.get(f"review_count_{k}_tacos") or 0)
        if not n:
            continue
        try:
            d = get(f"{base}/reviews/?rating={k}", ref)
            cs = [s for s in (slim(c) for c in (d.get("comments") or [])) if s]
            out["buckets"][str(k)] = {"expected": n,
                                      "reported_total": (d.get("meta") or {}).get("total"),
                                      "returned": len(cs), "comments": cs}
            if len(cs) < n:
                out["capped"].append({"rating": k, "expected": n, "returned": len(cs)})
        except Exception as e:
            out["buckets"][str(k)] = {"error": str(e)[:120]}
    return out


def main():
    recs = [json.loads(l) for l in open(os.path.join(HERE, "details.jsonl")) if l.strip()]
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            line = line.strip()
            if line:
                try:
                    done.add(json.loads(line)["deal_id"])
                except Exception:
                    pass
        print(f"resuming: {len(done)} on disk", file=sys.stderr)
    todo = [r for r in recs if r["id"] not in done]
    print(f"fetching 4-5 star reviews for {len(todo)} products", file=sys.stderr)

    errors, ok, nrev = [], 0, 0
    with open(OUT, "a") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(crawl_one, r): r for r in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            r = futs[f]
            try:
                res = f.result()
                fh.write(json.dumps(res, ensure_ascii=False) + "\n")
                fh.flush()
                ok += 1
                nrev += sum(len(b.get("comments") or []) for b in res["buckets"].values())
            except Exception as e:
                errors.append((r["slug"], str(e)[:160]))
            if i % 30 == 0:
                print(f"  {i}/{len(todo)} ok={ok} err={len(errors)} reviews={nrev}",
                      file=sys.stderr, flush=True)

    print(f"\nDONE products={ok} errors={len(errors)} positive_reviews={nrev} "
          f"on_disk={sum(1 for _ in open(OUT))}/{len(recs)}", file=sys.stderr)
    for e in errors[:15]:
        print("  ERR", e, file=sys.stderr)
    json.dump(errors, open(os.path.join(HERE, "positive_errors.json"), "w"), indent=1)


main()
