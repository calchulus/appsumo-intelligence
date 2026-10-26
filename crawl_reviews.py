"""Step 3: fetch review + question text.

The reviews endpoint hard-caps at 20 records and ignores page/per_page/offset/sort,
BUT honours `rating=N`. Negative reviews are the minority (2,789 of 24,797) and only
24 product-buckets exceed 20, so fetching rating=1,2,3 yields near-complete coverage
of the painpoint-bearing text. Also fetches the default recent-20 (for positive
themes) and the 20 most recent pre-purchase questions.
"""
import json, os, subprocess, sys, time
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
OUT = os.path.join(HERE, "reviews.jsonl")
WORKERS = 6
# NOTE: reviewer identity is deliberately NOT captured. See strip_pii.py and README.
KEEP = ["id", "created", "modified", "title", "comment", "rating", "would_recommend",
        "up_votes", "down_votes", "incentivized", "purchased", "level", "parent_id",
        "approved", "resolved", "answer_type"]


def slim(c):
    if not isinstance(c, dict):
        return None
    o = {k: c.get(k) for k in KEEP if c.get(k) is not None}
    kids = [slim(k) for k in (c.get("children") or [])]
    if kids:
        o["children"] = [k for k in kids if k]
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
           "buckets": {}, "recent": [], "questions": [], "capped": []}

    # recent-20 (mixed ratings) — positive themes + latest sentiment
    d = get(f"{base}/reviews/", ref)
    out["recent"] = [s for s in (slim(c) for c in (d.get("comments") or [])) if s]
    out["recent_total"] = (d.get("meta") or {}).get("total")

    # rating buckets 1..3 only: these carry the painpoints and are mostly complete
    # (just 24 product-buckets site-wide exceed the 20-record cap). 4/5 are skipped -
    # the recent-20 fetch above already samples positives, and those buckets are capped.
    for k in range(1, 4):
        n = int(dr.get(f"review_count_{k}_tacos") or 0)
        if not n:
            continue
        try:
            d = get(f"{base}/reviews/?rating={k}", ref)
            cs = [s for s in (slim(c) for c in (d.get("comments") or [])) if s]
            got_total = (d.get("meta") or {}).get("total")
            out["buckets"][str(k)] = {"expected": n, "reported_total": got_total,
                                      "returned": len(cs), "comments": cs}
            if len(cs) < n:
                out["capped"].append({"rating": k, "expected": n, "returned": len(cs)})
        except Exception as e:
            out["buckets"][str(k)] = {"error": str(e)[:120]}

    # pre-purchase questions (capped at 20 most recent)
    try:
        d = get(f"{base}/questions/", ref)
        out["questions"] = [s for s in (slim(c) for c in (d.get("comments") or [])) if s]
        out["questions_total"] = (d.get("meta") or {}).get("total")
    except Exception as e:
        out["questions_error"] = str(e)[:120]
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
    print(f"fetching reviews/questions for {len(todo)} products", file=sys.stderr)

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
                nrev += len(res["recent"]) + sum(
                    len(b.get("comments") or []) for b in res["buckets"].values())
            except Exception as e:
                errors.append((r["slug"], str(e)[:160]))
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} ok={ok} err={len(errors)} reviews={nrev}",
                      file=sys.stderr, flush=True)

    print(f"\nDONE products={ok} errors={len(errors)} review_records={nrev} "
          f"on_disk={sum(1 for _ in open(OUT))}/{len(recs)}", file=sys.stderr)
    for e in errors[:15]:
        print("  ERR", e, file=sys.stderr)
    json.dump(errors, open(os.path.join(HERE, "review_errors.json"), "w"), indent=1)


main()
