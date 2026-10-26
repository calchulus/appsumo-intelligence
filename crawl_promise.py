"""Step 6a: fetch the FULL vendor promise text per product.

pages.jsonl only kept plans. The real marketing claims live in the product page's
deal.products[0].story (html_body ~10 KB, tldr_overview, features.items, highlights),
deal.faqs (vendor's own Q&A), and deal.overview_media[].html_body. Without these,
claim detection covers only ~17% of the actual claims (e.g. "unlimited" 19 -> 111).
"""
import asyncio, html as htmllib, json, os, re, subprocess, sys, time
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
OUT = os.path.join(HERE, "promise.jsonl")
WORKERS = 6
NX = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)
MAXLEN = 14000


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', str(s))
    s = htmllib.unescape(re.sub(r'(?s)<[^>]+>', '\n', s))
    s = re.sub(r'[ \t]+', ' ', s)
    return re.sub(r'\n{2,}', '\n', s).strip()


def fetch(slug, tries=4):
    url = f"https://appsumo.com/products/{slug}/"
    last = None
    for t in range(tries):
        r = subprocess.run(["curl", "-sS", "-m", "60", "-A", UA, url],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            m = NX.search(r.stdout)
            if m:
                try:
                    d = json.loads(m.group(1))["props"]["pageProps"]["deal"]
                    story = ((d.get("products") or [{}])[0].get("story") or {})
                    feats = (story.get("features") or {}).get("items") or []
                    faqs = [{"q": (f.get("question") or "").strip(),
                             "a": strip_html(f.get("answer"))[:900]}
                            for f in (d.get("faqs") or []) if f.get("question")]
                    out = {
                        "slug": slug,
                        "deal_slug": d.get("slug"),
                        "deal_id": d.get("id"),
                        "public_name": d.get("public_name"),
                        "header": story.get("header"),
                        "subheader": story.get("subheader"),
                        "value_prop": story.get("value_prop"),
                        "meta_title": story.get("meta_title"),
                        "tldr": (story.get("tldr_overview") or "")[:2000],
                        "highlights": [h.get("highlight") for h in (story.get("highlights") or [])
                                       if h.get("highlight")],
                        "feature_blocks": [{"title": f.get("title"),
                                            "bullets": [re.sub(r"\s+", " ", b or "").strip()
                                                        for b in (f.get("bullets") or [])]}
                                           for f in feats if f.get("title")],
                        "body": strip_html(story.get("html_body"))[:MAXLEN],
                        "overview": strip_html(" ".join(o.get("html_body") or ""
                                             for o in (d.get("overview_media") or [])))[:MAXLEN],
                        "faqs": faqs,
                        "reviews_summary": d.get("reviews_summary"),
                    }
                    return out
                except Exception as e:
                    last = f"parse: {e}"
            else:
                last = f"no __NEXT_DATA__ ({len(r.stdout)}B)"
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
        print(f"resuming: {len(done)} on disk", file=sys.stderr)
    todo = [s for s in targets if s not in done]
    print(f"fetching full promise text for {len(todo)} products", file=sys.stderr)

    errors, ok, mismatch, chars = [], 0, [], 0
    with open(OUT, "a") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch, s): s for s in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            s = futs[f]
            try:
                rec = f.result()
                if rec.get("deal_slug") and rec["deal_slug"] != s:
                    mismatch.append((s, rec["deal_slug"]))
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                ok += 1
                chars += len(rec.get("body") or "") + len(rec.get("overview") or "")
            except Exception as e:
                errors.append((s, str(e)[:160]))
            if i % 40 == 0:
                print(f"  {i}/{len(todo)} ok={ok} err={len(errors)}", file=sys.stderr, flush=True)

    recs = [json.loads(l) for l in open(OUT) if l.strip()]
    print(f"\nDONE ok_this_run={ok} errors={len(errors)} mismatches={len(mismatch)} "
          f"on_disk={len(recs)}/{len(targets)}", file=sys.stderr)
    print(f"promise text volume: {sum(len(r.get('body') or '')+len(r.get('overview') or '') for r in recs)/1e6:.2f}M chars",
          file=sys.stderr)
    print(f"products with body text: {sum(1 for r in recs if r.get('body'))}/{len(recs)}", file=sys.stderr)
    print(f"products with faqs: {sum(1 for r in recs if r.get('faqs'))}/{len(recs)} "
          f"(total {sum(len(r.get('faqs') or []) for r in recs)} Q&A)", file=sys.stderr)
    print(f"products with feature_blocks: {sum(1 for r in recs if r.get('feature_blocks'))}/{len(recs)}",
          file=sys.stderr)
    for e in errors[:10]:
        print("  ERR", e, file=sys.stderr)
    json.dump({"errors": errors, "mismatches": mismatch},
              open(os.path.join(HERE, "promise_errors.json"), "w"), indent=1)


main()
