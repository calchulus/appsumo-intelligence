"""Step 2: fetch each product page and pull plans/tier ladder + review & question samples
out of its __NEXT_DATA__. The id-based API omits `plans`, so the page is the only source.
"""
import json, os, re, subprocess, sys, time
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
OUT = os.path.join(HERE, "pages.jsonl")
WORKERS = 6
NX = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)

COMMENT_KEYS = ["id", "created", "title", "comment", "rating", "would_recommend",
                "up_votes", "down_votes", "incentivized", "purchased", "level",
                "parent_id", "answer_type"]


def slim(c):
    if not isinstance(c, dict):
        return None
    o = {k: c.get(k) for k in COMMENT_KEYS if c.get(k) is not None}
    # reviewer identity deliberately NOT captured - see strip_pii.py
    kids = [slim(k) for k in (c.get("children") or [])]
    if kids:
        o["children"] = [k for k in kids if k]
    return o


def fetch_page(slug, tries=4):
    url = f"https://appsumo.com/products/{slug}/"
    last = None
    for t in range(tries):
        r = subprocess.run(["curl", "-sS", "-m", "60", "-A", UA, url],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            m = NX.search(r.stdout)
            if m:
                try:
                    pp = json.loads(m.group(1))["props"]["pageProps"]
                    deal = pp.get("deal") or {}
                    out = {
                        "slug": slug,
                        "deal_id": deal.get("id"),
                        "deal_slug": deal.get("slug"),
                        "public_name": deal.get("public_name"),
                        "plans": deal.get("plans") or [],
                        "plan_stack_count": deal.get("plan_stack_count"),
                        "availability": deal.get("availability"),
                        "codes_remaining": deal.get("codes_remaining"),
                        "product_url": deal.get("product_url"),
                        "refundable_days": deal.get("refundable_days"),
                        "reviews_meta": (pp.get("reviews") or {}).get("meta"),
                        "questions_meta": (pp.get("questions") or {}).get("meta"),
                        "reviews": [s for s in (slim(c) for c in
                                    ((pp.get("reviews") or {}).get("comments") or [])) if s],
                        "questions": [s for s in (slim(c) for c in
                                      ((pp.get("questions") or {}).get("comments") or [])) if s],
                    }
                    return out
                except Exception as e:
                    last = f"parse: {e}"
            else:
                last = f"no __NEXT_DATA__ (body {len(r.stdout)}B)"
        else:
            last = f"curl rc={r.returncode} {r.stderr[:100]}"
        time.sleep(1.2 * (t + 1))
    raise RuntimeError(f"{slug}: {last}")


def main():
    master = json.load(open(os.path.join(HERE, "appsumo_all_products.json")))
    targets = [p["slug"] for p in master["products"]]
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            line = line.strip()
            if line:
                try:
                    done.add(json.loads(line)["slug"])
                except Exception:
                    pass
        print(f"resuming: {len(done)} already on disk", file=sys.stderr)
    todo = [s for s in targets if s not in done]
    print(f"fetching {len(todo)} product pages ({len(targets)} total)", file=sys.stderr)

    errors, ok, mismatch = [], 0, []
    with open(OUT, "a") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch_page, s): s for s in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            s = futs[f]
            try:
                rec = f.result()
                # identity guard: the page must be about the slug we asked for
                if rec.get("deal_slug") and rec["deal_slug"] != s:
                    mismatch.append((s, rec["deal_slug"]))
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                ok += 1
            except Exception as e:
                errors.append((s, str(e)[:160]))
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} (ok={ok} err={len(errors)})", file=sys.stderr, flush=True)

    total = sum(1 for _ in open(OUT))
    print(f"\nDONE ok_this_run={ok} errors={len(errors)} slug_mismatches={len(mismatch)} "
          f"records_on_disk={total}/{len(targets)}", file=sys.stderr)
    for e in errors[:15]:
        print("  ERR", e, file=sys.stderr)
    for m in mismatch[:10]:
        print("  MISMATCH", m, file=sys.stderr)
    json.dump({"errors": errors, "mismatches": mismatch},
              open(os.path.join(HERE, "page_errors.json"), "w"), indent=1)


main()
