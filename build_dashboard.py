"""Step 5: build the self-contained searchable HTML dashboard from analysis.json.

Emits a BODY-ONLY fragment (no doctype/html/head/body) with all CSS+JS inline and
the dataset embedded as JSON, per the Artifact publishing contract.
"""
import json, os, sys, collections
from summary_text import TAKEAWAYS, SOWHAT, CONFIDENCE, CAMPAIGN_LESSONS as SYNTH4

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "appsumo_dashboard.html")

A = json.load(open(os.path.join(HERE, "analysis.json")))
P = A["products"]

KEEP = ["deal_id", "name", "slug", "url", "tagline", "group", "category", "subcategory",
        "listing", "is_free", "price_usd", "original_price_usd", "discount_pct",
        "plus_price_usd", "rating", "reviews", "start_date", "alternative_to", "best_for",
        "review_summary", "product_url", "availability", "refundable_days", "comment_count",
        "plan_stack_count", "tier_count", "entry_price", "top_price", "wtp_ratio",
        "ladder_shape", "ladder", "core_features", "common_features", "plan_terms",
        "feature_matrix", "sold_estimate", "sales_method", "active_codes", "codes_remaining",
        "review_count", "stars", "est_revenue_at_entry", "neg_reviews_analyzed",
        "neg_reviews_expected", "review_fetch_capped", "pain_themes", "pain_quotes",
        "questions_total", "questions_sampled", "questions_sample", "question_themes",
        "promise", "pos_themes", "pos_quotes", "fulfillment"]

prods = []
for p in P:
    o = {k: p.get(k) for k in KEEP}
    # trim quote payload: 8 per product, shorter opening text
    o["pain_quotes"] = [{**q, "text": (q.get("text") or "")[:200]}
                        for q in (p.get("pain_quotes") or [])[:8]]
    o["pos_quotes"] = [{**q, "text": (q.get("text") or "")[:200]}
                       for q in (p.get("pos_quotes") or [])[:8]]
    o["questions_sample"] = [q[:200] for q in (p.get("questions_sample") or [])[:4]]
    prods.append(o)

negtot = sum(p["neg_reviews_analyzed"] for p in P)
qtot = sum(p["questions_sampled"] for p in P)
coded = [p for p in P if p["sales_method"] == "codes" and p["sold_estimate"]]

# ---- derived rollups for the insights panel
groups = sorted({p["group"] or "(uncategorized)" for p in P})
cats = sorted({(p["group"] or "", p["category"] or "") for p in P if p["category"]})

pain = [{"k": k, "label": A["pain_theme_labels"][k], "n": n, "pct": round(n * 100 / negtot, 1)}
        for k, n in A["pain_theme_totals"].items()]
ques = [{"k": k, "label": A["question_theme_labels"][k], "n": n, "pct": round(n * 100 / qtot, 1)}
        for k, n in A["question_theme_totals"].items()]

# category x theme matrix
catneg = collections.Counter()
cattheme = collections.defaultdict(collections.Counter)
for p in P:
    c = p["category"] or "(uncategorized)"
    catneg[c] += p["neg_reviews_analyzed"]
    for t in p["pain_themes"]:
        cattheme[c][t["theme"]] += t["n"]
catrows = [{"cat": c, "neg": catneg[c],
            "top": [{"k": k, "n": n} for k, n in cattheme[c].most_common(3)]}
           for c in sorted(catneg, key=lambda x: -catneg[x])]

shapes = collections.Counter(p["ladder_shape"] for p in P if p["ladder_shape"])
ratios = sorted(p["wtp_ratio"] for p in P if p["wtp_ratio"])

# ---- promise-vs-delivery rollups
postot = sum(p["fulfillment"]["pos_analyzed"] for p in P)
pos_themes = [{"k": k, "label": A["pos_theme_labels"][k], "n": n,
               "pct": round(n * 100 / postot, 1)} for k, n in A["pos_theme_totals"].items()]
judge = [p for p in P if p["fulfillment"]["reviews_total"] >= 10]
bands = collections.Counter()
for p in judge:
    s = p["fulfillment"]["satisfaction_rate"]
    bands["95-100" if s >= 95 else "90-95" if s >= 90 else "80-90" if s >= 80
          else "70-80" if s >= 70 else "<70"] += 1
BAND_ORDER = ["95-100", "90-95", "80-90", "70-80", "<70"]
explicit_n = sum(1 for p in judge if p["fulfillment"]["explicit_delivers"] > 0)
pf = [p["fulfillment"]["promise_fail_pct"] for p in judge
      if p["neg_reviews_analyzed"] >= 5 and p["fulfillment"]["promise_fail_pct"] is not None]
pf.sort()

# ---- promise-vs-complaint cross-reference (crossref.py output)
X = json.load(open(os.path.join(HERE, "promise_crossref.json")))
CH = json.load(open(os.path.join(HERE, "campaign_highlights.json")))    # campaign ECONOMICS
CP = json.load(open(os.path.join(HERE, "campaign_participation.json")))  # campaign HISTORY
xrows = []
for r in X["rows"]:
    xrows.append({
        "deal_id": r["deal_id"], "name": r["name"], "slug": r["slug"], "url": r["url"],
        "category": r["category"], "group": r["group"], "satisfaction": r["satisfaction"],
        "rating": r["rating"], "review_count": r["review_count"], "neg_reviews": r["neg_reviews"],
        "sold_estimate": r["sold_estimate"], "entry_price": r["entry_price"],
        "n": r["n_contradicted_claims"],
        "promise": {k: r["promise"].get(k) for k in ("value_prop", "subheader")},
        "claims": [{"k": h["claim"], "label": h["label"], "promised": h["promised"],
                    "n": h["n_reviews"],
                    "ex": [{**e, "ctx": (e.get("ctx") or "")[:230]} for e in h["examples"][:3]]}
                   for h in r["contradictions"]],
    })
xarch = [{"k": k, "label": X["archetype_labels"][k], **v}
         for k, v in X["archetype_stats"].items() if v["claims"]]
xarch.sort(key=lambda a: -(a["contradiction_rate"] or 0))

DATA = {
    "meta": {
        "generated": "2026-10-26",
        "products": len(prods),
        "categories": len({c for _, c in cats}),
        "groups": groups,
        "neg_reviews": negtot,
        "neg_expected": sum(p["neg_reviews_expected"] for p in P),
        "questions": qtot,
        "questions_total_available": sum(p["questions_total"] or 0 for p in P),
        "total_reviews": sum(sum((p["stars"] or {}).values()) for p in P),
        "sales_method_counts": A["sales_method_counts"],
        "coded_units": sum(p["sold_estimate"] for p in coded),
        "coded_revenue": sum(p["est_revenue_at_entry"] or 0 for p in coded),
        # codes != purchases: 418 of 1,057 tiers grant >1 code per purchase.
        # paid codes exclude the $0 lead magnets that still use a code system.
        "paid_codes": CH["aggregate"]["total_units_paid"],
        "free_codes": CH["aggregate"]["total_units_free"],
        "paid_campaigns": CH["aggregate"]["paid_campaigns"],
        "gross_rev_point": CH["aggregate"]["gross_rev_point"],
        "gross_rev_floor": CH["aggregate"]["gross_rev_floor"],
        "gross_rev_ceiling": CH["aggregate"]["gross_rev_ceiling"],
        "median_days_live": CH["aggregate"]["median_days_live"],
        "campaigns": CP,
        "capped_products": sum(1 for p in P if p["review_fetch_capped"]),
        "pos_reviews": postot,
        "pos_expected": sum((p["stars"] or {}).get("4", 0) + (p["stars"] or {}).get("5", 0) for p in P),
        "judgeable": len(judge),
        "explicit_confirm": explicit_n,
        "sat_median": round(sorted(p["fulfillment"]["satisfaction_rate"] for p in judge)[len(judge) // 2], 1),
        "sat_mean": round(sum(p["fulfillment"]["satisfaction_rate"] for p in judge) / len(judge), 1),
        "promise_fail_median": round(pf[len(pf) // 2]) if pf else None,
        "anticipatory_pct": round(A["pos_theme_totals"].get("anticipatory", 0) * 100 / postot, 1),
        "xref_products": X["products_with_contradiction"],
        "xref_reviews": X["total_contradiction_reviews"],
        "xref_mismatch_stated": X["archetype_stats"]["explicit_mismatch"]["reviews"],
        "boilerplate_filtered": X["boilerplate_terms_filtered"],
    },
    "xref_arch": xarch,
    "xref_rows": xrows,
    "pain_themes": pain,
    "question_themes": ques,
    "pos_themes": pos_themes,
    "pain_labels": A["pain_theme_labels"],
    "question_labels": A["question_theme_labels"],
    "pos_labels": A["pos_theme_labels"],
    "theme_quotes": {k: [{**q, "text": (q.get("text") or "")[:180]}
                         for q in v[:10]] for k, v in A["theme_quotes"].items()},
    "pos_theme_quotes": {k: [{**q, "text": (q.get("text") or "")[:180]}
                             for q in v[:10]] for k, v in A["pos_theme_quotes"].items()},
    "sat_bands": [{"k": b, "n": bands.get(b, 0)} for b in BAND_ORDER],
    "catrows": catrows,
    "ladder_shapes": dict(shapes),
    "ratio_median": ratios[len(ratios) // 2] if ratios else None,
    "ratio_max": max(ratios) if ratios else None,
    "products": prods,
}

blob = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
print(f"embedded payload: {len(blob)/1e6:.2f} MB", file=sys.stderr)

HTML = """
<style>
.asd{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;
  --blue:#1e3a8a;--orange:#b45309;--green:#166534;--rose:#be123c;
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink);background:var(--bg);padding:0 0 60px}
.asd *{box-sizing:border-box}
.asd h1{font-size:26px;margin:0 0 4px;letter-spacing:-.4px}
.asd h2{font-size:18px;margin:0 0 3px;letter-spacing:-.2px}
.asd h3{font-size:14px;margin:18px 0 8px;text-transform:uppercase;letter-spacing:.7px;color:var(--mut)}
.asd .sub{color:var(--mut);margin:0 0 18px;font-size:13.5px}
.asd .wrap{max-width:1240px;margin:0 auto;padding:0 18px}
.asd .chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 6px}
.asd .chip{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 13px;min-width:112px}
.asd .chip b{display:block;font-size:19px;letter-spacing:-.4px}
.asd .chip span{font-size:11.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px}
.asd nav{position:sticky;top:0;z-index:20;background:rgba(248,250,252,.94);backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line);margin:18px 0 22px}
.asd nav .wrap{display:flex;gap:4px;padding:0 18px}
.asd nav button{background:none;border:0;border-bottom:2.5px solid transparent;padding:11px 15px;
  font:600 13.5px/1 inherit;color:var(--mut);cursor:pointer}
.asd nav button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--blue)}
.asd section[hidden]{display:none}
.asd .card{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:16px 18px;margin-bottom:14px}
.asd .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.asd .grid2{grid-template-columns:1fr}}
.asd table{width:100%;border-collapse:collapse;font-size:13px}
.asd th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:var(--mut);
  padding:7px 9px;border-bottom:1px solid var(--line);white-space:nowrap}
.asd td{padding:7px 9px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.asd tbody tr:hover{background:#fbfdff}
.asd .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.asd .bar{height:22px;background:var(--blue);border-radius:0 4px 4px 0;min-width:2px}
.asd .barrow{display:grid;grid-template-columns:minmax(150px,220px) 1fr 92px;gap:9px;align-items:center;margin-bottom:5px}
.asd .barlab{font-size:12.5px;text-align:right;color:var(--ink)}
.asd .barval{font-size:12px;color:var(--mut);font-variant-numeric:tabular-nums}
.asd .barwrap{background:#eef2f7;border-radius:4px;overflow:hidden}
.asd button.barwrap{border:0;padding:0;cursor:pointer;width:100%;text-align:left}
.asd button.barwrap:hover .bar{background:#2c4fa8}
.asd .tag{display:inline-block;background:#eef2f7;border-radius:20px;padding:1.5px 8px;font-size:11px;
  color:#334155;margin:0 4px 4px 0;white-space:nowrap}
.asd .tag.g{background:#dcfce7;color:#14532d}.asd .tag.o{background:#ffedd5;color:#7c2d12}
.asd .tag.r{background:#ffe4e6;color:#881337}.asd .tag.b{background:#dbeafe;color:#1e3a8a}
.asd .q{border-left:3px solid var(--line);padding:6px 0 6px 11px;margin:7px 0;font-size:12.8px;color:#334155}
.asd .q .who{display:block;font-size:11px;color:var(--mut);margin-top:3px}
.asd .q .hit{background:#fef3c7;border-radius:2px;padding:0 2px}
.asd .ctrl{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-bottom:14px}
.asd input[type=search],.asd select,.asd input[type=number]{font:13px inherit;padding:7px 9px;
  border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.asd input[type=search]{flex:1 1 250px;min-width:200px}
.asd label.f{display:flex;align-items:center;gap:5px;font-size:12.5px;color:var(--mut)}
.asd .prod{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:9px;overflow:hidden}
.asd .phead{display:grid;grid-template-columns:1fr auto;gap:10px;padding:12px 15px;cursor:pointer;align-items:start}
.asd .phead:hover{background:#fbfdff}
.asd .pname{font-weight:650;font-size:14.5px;letter-spacing:-.15px}
.asd .ptag{color:var(--mut);font-size:12.5px;margin-top:2px}
.asd .pnums{display:flex;gap:14px;align-items:baseline;font-variant-numeric:tabular-nums;white-space:nowrap}
.asd .pnums b{font-size:14px}.asd .pnums span{font-size:11px;color:var(--mut);display:block;text-align:right}
.asd .pbody{border-top:1px solid var(--line);padding:15px;background:#fcfdfe;display:grid;
  grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.asd .pbody{grid-template-columns:1fr}.asd .phead{grid-template-columns:1fr}}
.asd ul.feat{margin:5px 0;padding-left:18px;font-size:12.8px}
.asd ul.feat li{margin-bottom:3px}
.asd .fm{width:100%;font-size:12px}
.asd .fm td,.asd .fm th{padding:4px 7px;border:1px solid var(--line)}
.asd .fm th{background:#f1f5f9;text-transform:none;letter-spacing:0;font-size:11.5px}
.asd .note{font-size:12.3px;color:var(--mut);background:#f8fafc;border:1px solid var(--line);
  border-left:3px solid var(--orange);border-radius:6px;padding:9px 12px;margin:9px 0}
.asd .ok{border-left-color:var(--green)}
.asd .mut{color:var(--mut);font-size:11.5px;font-weight:400}
.asd .tblwrap{overflow-x:auto;margin:6px 0 4px}
.asd .chip div.mut{margin-top:3px;text-transform:none;letter-spacing:0}
.asd .syn p{margin:0 0 11px;font-size:13.6px}
.asd .syn strong{font-weight:650}
.asd code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
.asd .stars{color:var(--orange);letter-spacing:-1px}
.asd .empty{padding:34px;text-align:center;color:var(--mut)}
.asd .mut{font-size:11.5px;color:var(--mut);font-weight:400}
.asd .tblwrap{overflow-x:auto}
.asd td.r,.asd th.r{text-align:right}
.asd .chip .mut{margin-top:2px;text-transform:none;letter-spacing:0;font-size:11px}
.asd .chips{margin-bottom:10px}
.asd a{color:var(--blue)}
.asd .tk{display:grid;grid-template-columns:30px 1fr;gap:12px;padding:13px 0;border-top:1px solid var(--line)}
.asd .tk:first-child{border-top:0}
.asd .tkn{font-size:12px;font-weight:700;color:#fff;background:var(--blue);border-radius:50%;
  width:26px;height:26px;display:flex;align-items:center;justify-content:center}
.asd .tk h4{margin:0 0 4px;font-size:14.5px;letter-spacing:-.15px}
.asd .tk p{margin:0;font-size:13.2px;color:#334155}
.asd .tk .ev{display:block;margin-top:5px;font-size:11.5px;color:var(--mut)}
.asd .tk .ev b{color:var(--orange);font-weight:600}
.asd .xr{border:1px solid var(--line);border-radius:9px;margin-bottom:9px;background:#fff}
.asd .xrh{padding:11px 14px;cursor:pointer;display:grid;grid-template-columns:1fr auto;gap:10px}
.asd .xrh:hover{background:#fbfdff}
.asd .xrb{border-top:1px solid var(--line);padding:13px 15px;background:#fcfdfe}
.asd .pair{border-left:3px solid var(--rose);padding:7px 0 7px 11px;margin:9px 0}
.asd .pair .cl{font-size:12.4px;color:#334155}
.asd .pair .cl b{color:var(--rose);font-weight:650}
.asd .pair .cm{font-size:12.6px;margin-top:5px;color:var(--ink)}
.asd .pair .who{display:block;font-size:11px;color:var(--mut);margin-top:3px}
.asd .pill{display:inline-block;border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600;margin:0 4px 4px 0}
.asd .pill.hi{background:#ffe4e6;color:#881337}.asd .pill.md{background:#ffedd5;color:#7c2d12}
.asd .pill.lo{background:#eef2f7;color:#334155}
</style>

<div class="asd">
<div class="wrap">
  <h1>AppSumo catalog intelligence</h1>
  <p class="sub">Every live product across all 27 browse categories — features, price ladders,
     derived sales volume, and painpoints mined from real customer reviews. Snapshot <b id="gen"></b>.</p>
  <div class="chips" id="chips"></div>
</div>

<nav><div class="wrap" role="tablist">
  <button role="tab" aria-selected="true" data-t="summary">Summary</button>
  <button role="tab" aria-selected="false" data-t="insights">Insights</button>
  <button role="tab" aria-selected="false" data-t="promise">Promise vs delivery</button>
  <button role="tab" aria-selected="false" data-t="claims">Claims vs complaints</button>
  <button role="tab" aria-selected="false" data-t="campaigns">Campaign highlights</button>
  <button role="tab" aria-selected="false" data-t="browse">Browse products</button>
  <button role="tab" aria-selected="false" data-t="method">Method &amp; caveats</button>
</div></nav>

<section id="summary"><div class="wrap">
  <div class="card">
    <h2>Key takeaways</h2>
    <p class="sub">Everything below is derived from AppSumo's own JSON APIs on 2026-10-26 —
      <b id="sProds"></b> live products across all 27 browse categories, <b id="sRevText"></b>
      review texts read verbatim, <b id="sUnits"></b> license codes (of <b id="sUnitsAll"></b>
      total issued across <b id="sCamp"></b> promotional campaigns). Each takeaway names the
      tab that evidences it.</p>
    <div id="keyTakeaways"></div>
  </div>
  <div class="grid2">
    <div class="card">
      <h2>The numbers at a glance</h2>
      <div style="overflow-x:auto"><table id="glanceTable"></table></div>
    </div>
    <div class="card">
      <h2>What to do with this</h2>
      <div id="soWhat"></div>
    </div>
  </div>
  <div class="card">
    <h2>Confidence &amp; known limits</h2>
    <div id="confBox"></div>
  </div>
</div></section>

<section id="insights" hidden><div class="wrap">
  <div class="card">
    <h2>What buyers complain about, ranked</h2>
    <p class="sub" id="painSub"></p>
    <div id="painChart"></div>
    <p class="sub" style="margin-top:9px">Click any bar for verbatim quotes. Counts are
      <b>mentions, not complaints</b> — a negative review can trip several themes, and a theme
      keyword occasionally lands in a positive clause inside an otherwise negative review.</p>
  </div>

  <div class="card">
    <h2>What buyers ask before paying</h2>
    <p class="sub" id="qSub"></p>
    <div id="qChart"></div>
  </div>

  <div class="card">
    <h2>Sales volume — derived, not published</h2>
    <p class="sub">AppSumo exposes no <code>units_sold</code> field. Units are derived as
      <code>active_codes &minus; codes_remaining</code>, validated against the site's own freebie
      download counts at <b>0.3% median error</b>. Covers <b id="covN"></b> of 342 products;
      the remainder use no code system and are ranked separately by review count.</p>
    <h3>Top 25 by derived <em>paid</em> units sold</h3>
    <div style="overflow-x:auto"><table id="soldTable"></table></div>
    <h3>Most-claimed free items — lead magnets, not sales</h3>
    <p class="sub" style="margin-top:0">Kept separate on purpose: these download counts are an
      order of magnitude above paid volume and would swamp any combined ranking.</p>
    <div style="overflow-x:auto"><table id="dlTable"></table></div>
    <h3>Highest review counts among the 133 with no codes signal</h3>
    <div style="overflow-x:auto"><table id="revTable"></table></div>
  </div>

  <div class="card">
    <h2>Willingness to pay</h2>
    <p class="sub" id="wtpSub"></p>
    <div class="grid2">
      <div><h3>Ladder architecture</h3><div id="shapeBox"></div>
        <p class="sub" style="margin-top:8px"><b>Linear</b> = flat price per added code
        ($49/$98/$147…), pure agency stacking. <b>Progressive</b> = jumps steepen, segmenting
        buyers by size.</p></div>
      <div><h3>Top-tier ceiling vs entry price</h3>
        <div style="overflow-x:auto"><table id="ceilTable"></table></div></div>
    </div>
  </div>

  <div class="card">
    <h2>Where each category hurts</h2>
    <p class="sub">Negative-review volume by category with its three most-mentioned themes.</p>
    <div style="overflow-x:auto"><table id="catTable"></table></div>
  </div>

  <div class="card">
    <h2>Proven volume, poor delivery</h2>
    <p class="sub">Products with &ge;50 reviews and the lowest ratings — real demand meeting
      real dissatisfaction.</p>
    <div style="overflow-x:auto"><table id="badTable"></table></div>
  </div>

  <div class="card syn">
    <h2>What the data says</h2>
    <div id="synth"></div>
  </div>
</div></section>

<section id="promise" hidden><div class="wrap">
  <div class="card">
    <h2>Does the product actually do the job it was sold to do?</h2>
    <p class="sub">Each vendor's own promise (value proposition, listing highlights, stated
      audience, named rivals) set against what buyers say afterwards. Built from
      <b id="posN"></b> positive reviews (4–5★) and <b id="negN"></b> negative reviews (1–3★).</p>
    <div class="note"><b>Read this first.</b> Satisfaction below comes from AppSumo's
      <em>complete</em> star breakdown, so it is exact. But the API returns at most 20 records per
      rating bucket, so the positive <em>text</em> is a sample: <b id="posCov"></b> of the
      4–5★ reviews on site. Negative text is far better covered, because negatives are rare —
      <b id="negCov"></b>. Treat praise-theme percentages as a sample, satisfaction rates as exact.</div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>What buyers praise</h2>
      <p class="sub" id="posSub"></p>
      <div id="posChart"></div>
      <p class="sub" style="margin-top:9px">Click a bar for verbatim quotes. The last two entries
        are <b>not</b> praise — they flag reviews that cannot corroborate the promise.</p>
    </div>
    <div class="card">
      <h2>Satisfaction distribution</h2>
      <p class="sub" id="satSub"></p>
      <div id="satChart"></div>
      <p class="sub" style="margin-top:9px">Share of each product's reviews that are 4–5★, from
        AppSumo's complete star counts. Only the <b id="judgeN"></b> products with ≥10 reviews are
        binned — below that a single review swings the rate wildly.</p>
    </div>
  </div>

  <div class="card">
    <h2>The corroboration gap</h2>
    <div id="gapBox"></div>
  </div>

  <div class="card">
    <h2>Best-evidenced promise fulfilment</h2>
    <p class="sub">≥95% satisfaction <em>and</em> at least three buyers explicitly saying it does
      the promised job. Sorted by explicit confirmations, then review volume.</p>
    <div style="overflow-x:auto"><table id="bestTable"></table></div>
  </div>

  <div class="card">
    <h2>Promise failures — the product doesn't do the job</h2>
    <p class="sub">Highest share of negative reviews whose complaint is about the
      <em>core promise</em> (missing feature / broken / deal devalued) rather than the delivery
      around it (support, refunds, UI, setup, limits). Requires ≥5 analysed negative reviews.</p>
    <div style="overflow-x:auto"><table id="failTable"></table></div>
  </div>

  <div class="card syn">
    <h2>What the promise-vs-delivery data says</h2>
    <div id="synth2"></div>
  </div>
</div></section>

<section id="claims" hidden><div class="wrap">
  <div class="card">
    <h2>Which vendor claims their own customers contradict</h2>
    <p class="sub">13 claim archetypes, each a <em>(promise pattern → contradiction pattern)</em>
      pair. A contradiction is only counted against a product that <b>actually made that claim</b> —
      a complaint about coding never counts against a product that didn't promise no-code.
      <b id="xrN"></b> of 342 products have at least one contradicted claim, across
      <b id="xrR"></b> negative reviews. Plus <b id="xrM"></b> reviews where the buyer states
      outright that the listing ≠ the product.</p>
    <div id="archChart"></div>
    <p class="sub" style="margin-top:9px">Rate = products contradicting that claim ÷ products that
      made it. Click a bar to see the verbatim pairs.</p>
  </div>

  <div class="card">
    <h2>Products ranked by distinct claims contradicted</h2>
    <div class="ctrl">
      <select id="xArch"><option value="">All claim types</option></select>
      <select id="xSort">
        <option value="n">Sort: claims contradicted</option>
        <option value="rev">Sort: contradicting reviews</option>
        <option value="sat">Sort: lowest satisfaction</option>
        <option value="neg">Sort: negative reviews read</option>
        <option value="sold">Sort: units sold</option>
      </select>
      <span class="barval" id="xCount"></span>
    </div>
    <div id="xList"></div>
  </div>

  <div class="card syn">
    <h2>What the cross-reference says</h2>
    <div id="synth3"></div>
  </div>
</div></section>

<section id="campaigns" hidden><div class="wrap">
  <div id="campBody"></div>

  <div class="card">
    <h2>The promotional calendar</h2>
    <p class="sub">Everything above is per-campaign economics. This is the other half of the
      <code>participation</code> data: <b>which sales events each product appeared in</b> —
      <b id="cN"></b> distinct campaigns across <b id="cY"></b>, on
      <b id="cP"></b> products.</p>
    <div id="kindChart"></div>
    <h3>Largest individual campaigns</h3>
    <div class="tblwrap"><table id="campTable"></table></div>
    <div class="note" id="gaEaNote"></div>
  </div>

  <div class="card">
    <h2>Does being promoted more actually sell more?</h2>
    <p class="sub">The raw correlation says yes — median codes rise from <b id="d0"></b> to
      <b id="d24"></b>. But that is largely a <em>tenure</em> artifact: older listings have simply
      been alive for more sales events. Controlling for launch cohort changes the answer.</p>
    <div class="grid2">
      <div><h3>Raw: promotion depth vs outcome</h3>
        <div class="tblwrap"><table id="depthTable"></table></div></div>
      <div><h3>Tenure-controlled: within each launch cohort</h3>
        <div class="tblwrap"><table id="tenureTable"></table></div>
        <div class="note" id="tenureNote"></div></div>
    </div>
  </div>

  <div class="card">
    <h2>What promotion depth does to complaints</h2>
    <p class="sub">Share of each band's negative reviews carrying each theme.</p>
    <div class="tblwrap"><table id="mixTable"></table></div>
    <div class="note" id="mixNote"></div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>The always-on roster</h2>
      <p class="sub">Products in ≥24 recurring campaigns. Volume and satisfaction diverge sharply
        here — the two biggest movers sit near 50% satisfaction.</p>
      <div class="tblwrap"><table id="alwaysTable"></table></div>
    </div>
    <div class="card">
      <h2>Recent launches (2025–2026 cohort)</h2>
      <p class="sub" id="recentSub"></p>
      <div class="tblwrap"><table id="recentTable"></table></div>
    </div>
  </div>

  <div class="card syn">
    <h2>Lessons for a team launching on AppSumo</h2>
    <div id="synth4"></div>
  </div>
</div></section>

<section id="browse" hidden><div class="wrap">
  <div class="ctrl">
    <input type="search" id="q" placeholder="Search name, tagline, features, painpoints, alternatives…">
    <select id="fGroup"><option value="">All groups</option></select>
    <select id="fCat"><option value="">All categories</option></select>
    <select id="fList"><option value="">All listing types</option>
      <option>AppSumo Select</option><option>Marketplace</option></select>
    <select id="fSort">
      <option value="sold">Sort: units sold (paid)</option>
      <option value="dl">Sort: downloads (free items)</option>
      <option value="rev">Sort: est. revenue</option>
      <option value="reviews">Sort: review count</option>
      <option value="rating">Sort: rating</option>
      <option value="entry">Sort: entry price</option>
      <option value="top">Sort: top-tier price</option>
      <option value="wtp">Sort: ceiling multiple</option>
      <option value="disc">Sort: discount</option>
      <option value="neg">Sort: negative reviews</option>
      <option value="sat">Sort: satisfaction (4–5★ share)</option>
      <option value="explicit">Sort: explicit “does the job”</option>
      <option value="pf">Sort: promise-focused complaints</option>
      <option value="antic">Sort: anticipatory praise</option>
      <option value="claims">Sort: claims contradicted</option>
      <option value="name">Sort: name A–Z</option>
    </select>
    <label class="f">Min rating <input type="number" id="fRating" min="0" max="5" step="0.1" style="width:66px"></label>
    <label class="f">Max entry $ <input type="number" id="fPrice" min="0" step="10" style="width:76px"></label>
    <label class="f"><input type="checkbox" id="fSold"> Has sales data</label>
    <span class="barval" id="count"></span>
  </div>
  <div id="list"></div>
</div></section>

<section id="method" hidden><div class="wrap">
  <div class="card">
    <h2>How this was built</h2>
    <p class="sub">Nine passes over AppSumo's own APIs on 2026-10-26. No page was scraped by
      rendering; every number comes from the JSON the site serves itself.</p>
    <div style="overflow-x:auto"><table id="srcTable"></table></div>
  </div>
  <div class="card">
    <h2>Coverage &amp; reconciliation</h2>
    <div id="covBox"></div>
  </div>
  <div class="card">
    <h2>Caveats — read before quoting numbers</h2>
    <div id="cavBox"></div>
  </div>
</div></section>
</div>

<script id="asd-data" type="application/json">__DATA__</script>
<script>
(function(){
const D=JSON.parse(document.getElementById('asd-data').textContent);
const P=D.products, M=D.meta;
const $=s=>document.querySelector(s), esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const money=n=>n==null?'—':(n>=1e6?'$'+(n/1e6).toFixed(2)+'M':n>=1e3?'$'+(n/1e3).toFixed(0)+'k':'$'+Math.round(n));
const num=n=>n==null?'—':Number(n).toLocaleString();
const stars=r=>r?('<span class="stars">'+'★'.repeat(Math.round(r))+'</span> '+Number(r).toFixed(2)):'—';

$('#gen').textContent=M.generated;

// ---------- header chips
$('#chips').innerHTML=[['Products',M.products],['Categories',M.categories],
 ['Live reviews',num(M.total_reviews)],['Negative reviews read',num(M.neg_reviews)],
 ['Questions read',num(M.questions)],['License codes issued',num(M.coded_units)],
 ['Est. revenue floor',money(M.coded_revenue)]]
 .map(([l,v])=>`<div class="chip"><b>${v}</b><span>${l}</span></div>`).join('');

// ---------- tabs
const TABS=['summary','insights','promise','claims','campaigns','browse','method'];
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('nav button').forEach(x=>x.setAttribute('aria-selected',x===b));
  TABS.forEach(id=>$('#'+id).hidden=(id!==b.dataset.t));
  window.scrollTo({top:0});
});

// ---------- bar charts
function bars(el,rows,onclick){
  const max=Math.max(...rows.map(r=>r.n));
  el.innerHTML=rows.map((r,i)=>`<div class="barrow">
    <div class="barlab">${esc(r.label)}</div>
    <button class="barwrap" data-i="${i}" title="click for quotes"><div class="bar" style="width:${(r.n/max*100).toFixed(1)}%"></div></button>
    <div class="barval">${num(r.n)} · ${r.pct}%</div></div>`).join('');
  if(onclick) el.querySelectorAll('button.barwrap').forEach(b=>b.onclick=()=>onclick(rows[+b.dataset.i],el));
}
function quoteBox(theme,host){
  const qs=(D.theme_quotes[theme]||[]);
  const ex=host.parentElement.querySelector('.qbox'); if(ex){ex.remove();return;}
  const d=document.createElement('div'); d.className='qbox';
  d.innerHTML=`<h3 style="margin-top:14px">Verbatim — ${esc(D.pain_labels[theme])}
    <span class="barval">(${qs.length} of ${num((D.pain_themes.find(t=>t.k===theme)||{}).n)} mentions)</span></h3>`+
    (qs.length?qs.map(q=>`<div class="q">${esc(q.ctx||q.text)}
      <span class="who">${esc(q.product)} · ${q.star}★ · ${q.up||0} helpful · matched “${esc(q.matched)}”</span></div>`).join('')
      :'<p class="sub">No quotes captured.</p>');
  host.parentElement.appendChild(d);
}
$('#painSub').textContent=`${num(M.neg_reviews)} negative reviews analysed — ${M.neg_expected?
  ((M.neg_reviews/M.neg_expected*100).toFixed(1)):'?'}% of all 1–3★ reviews AppSumo reports site-wide.`;
bars($('#painChart'),D.pain_themes,(r,el)=>quoteBox(r.k,el));
$('#qSub').textContent=`${num(M.questions)} most-recent pre-purchase questions read, of ${num(M.questions_total_available)} total on site (the API caps questions at 20 per product).`;
bars($('#qChart'),D.question_themes);

// ---------- tables
function tbl(el,head,rows){
  el.innerHTML=`<thead><tr>${head.map((h,i)=>`<th class="${i?'num':''}">${h}</th>`).join('')}</tr></thead>
   <tbody>${rows.map(r=>`<tr>${r.map((c,i)=>`<td class="${i?'num':''}">${c}</td>`).join('')}</tr>`).join('')}</tbody>`;
}
const sold=P.filter(p=>p.sales_method==='codes'&&p.sold_estimate).sort((a,b)=>b.sold_estimate-a.sold_estimate);
$('#covN').textContent=sold.length;
tbl($('#soldTable'),['Product','Units sold','Entry','Est. revenue','Rating','Reviews','Category'],
 sold.slice(0,25).map(p=>[esc(p.name),num(p.sold_estimate),money(p.entry_price),
  money(p.est_revenue_at_entry),stars(p.rating),num(p.review_count),esc(p.category||'—')]));
const dls=P.filter(p=>p.sales_method==='downloads'&&p.sold_estimate).sort((a,b)=>b.sold_estimate-a.sold_estimate);
tbl($('#dlTable'),['Free item','Downloads','Rating','Reviews','Category'],
 dls.slice(0,10).map(p=>[esc(p.name),num(p.sold_estimate),stars(p.rating),
  num(p.review_count),esc(p.category||'—')]));
const nc=P.filter(p=>!p.sold_estimate).sort((a,b)=>(b.review_count||0)-(a.review_count||0));

// ---------- insights: no-codes band, willingness to pay, category x theme, worst-rated
tbl($('#revTable'),['Product','Reviews','Rating','Entry','Top tier','Category'],
 nc.slice(0,15).map(p=>[esc(p.name),num(p.review_count),stars(p.rating),money(p.entry_price),
  money(p.top_price),esc(p.category||'—')]));
$('#wtpSub').textContent=`${num(P.filter(p=>p.ladder).length)} products publish a multi-tier ladder. Median top-tier ÷ entry = ${D.ratio_median}×; max ${D.ratio_max}×.`;
$('#shapeBox').innerHTML=Object.entries(D.ladder_shapes).map(([k,v])=>
 `<div class="barrow"><div class="barlab">${k==='linear'?'Linear (flat per code)':'Progressive (steepening)'}</div>
  <div class="barwrap"><div class="bar" style="width:${(v/Math.max(...Object.values(D.ladder_shapes))*100).toFixed(0)}%;background:var(--orange)"></div></div>
  <div class="barval">${v} products</div></div>`).join('');
tbl($('#ceilTable'),['Product','Top','Entry','×','Tiers','Shape','Codes'],
 P.filter(p=>p.sold_estimate&&p.top_price).sort((a,b)=>b.top_price-a.top_price).slice(0,12)
  .map(p=>[esc(p.name),money(p.top_price),money(p.entry_price),(p.wtp_ratio||'—')+'×',
   p.tier_count,esc(p.ladder_shape||'—'),num(p.sold_estimate)]));
tbl($('#catTable'),['Category','Neg. reviews','Top themes'],
 D.catrows.map(r=>[esc(r.cat),num(r.neg),
  r.top.map(t=>`<span class="tag">${esc((D.pain_labels[t.k]||t.k).split('/')[0].trim())} ${t.n}</span>`).join('')||'—']));
tbl($('#badTable'),['Product','Rating','Reviews','Codes','Entry','Dominant painpoints'],
 P.filter(p=>(p.review_count||0)>=50&&p.rating).sort((a,b)=>a.rating-b.rating).slice(0,15)
  .map(p=>[esc(p.name),stars(p.rating),num(p.review_count),
   p.sold_estimate?num(p.sold_estimate):'<span class="barval">no codes data</span>',money(p.entry_price),
   (p.pain_themes||[]).slice(0,3).map(t=>`<span class="tag r">${esc((D.pain_labels[t.theme]||t.theme).split('/')[0].trim())} ${t.n}</span>`).join('')||'—']));

// ---------- promise vs delivery tab
$('#posN').textContent=num(M.pos_reviews);
$('#negN').textContent=num(M.neg_reviews);
$('#posCov').textContent=num(M.pos_reviews)+' of '+num(M.pos_expected)+' ('+
  (M.pos_reviews/M.pos_expected*100).toFixed(1)+'%)';
$('#negCov').textContent=num(M.neg_reviews)+' of '+num(M.neg_expected)+' ('+
  (M.neg_reviews/M.neg_expected*100).toFixed(1)+'%)';
$('#judgeN').textContent=M.judgeable;
$('#posSub').textContent=`Share of ${num(M.pos_reviews)} sampled 4–5★ reviews mentioning each theme.`;
bars($('#posChart'),D.pos_themes,(r,el)=>{
  const qs=D.pos_theme_quotes[r.k]||[];
  const ex=el.parentElement.querySelector('.qbox'); if(ex){ex.remove();return;}
  const d=document.createElement('div'); d.className='qbox';
  d.innerHTML=`<h3 style="margin-top:14px">Verbatim — ${esc(r.label)}
    <span class="barval">(${qs.length} of ${num(r.n)} mentions)</span></h3>`+
   (qs.length?qs.map(q=>`<div class="q" style="border-left-color:var(--green)">${esc(q.ctx||q.text)}
     <span class="who">${esc(q.product)} · ${q.star}★ · ${q.up||0} helpful · matched “${esc(q.matched)}”</span></div>`).join('')
    :'<p class="sub">No quotes captured.</p>');
  el.parentElement.appendChild(d);
});
$('#satSub').textContent=`${M.judgeable} products with ≥10 reviews. Median satisfaction ${M.sat_median}%, mean ${M.sat_mean}%.`;
const satMax=Math.max(...D.sat_bands.map(b=>b.n));
$('#satChart').innerHTML=D.sat_bands.map(b=>{
  const col=(b.k==='95-100'||b.k==='90-95')?'var(--green)':b.k==='80-90'?'var(--blue)':
            b.k==='70-80'?'var(--orange)':'var(--rose)';
  return `<div class="barrow"><div class="barlab">${b.k}% of reviews are 4–5★</div>
   <div class="barwrap"><div class="bar" style="width:${(b.n/satMax*100).toFixed(1)}%;background:${col}"></div></div>
   <div class="barval">${b.n} products</div></div>`;}).join('');
const dp=D.pos_themes.find(t=>t.k==='delivers_promise')||{n:0,pct:0};
const es=D.pos_themes.find(t=>t.k==='ease_speed')||{n:0,pct:0};
$('#gapBox').innerHTML=`
 <div class="note"><b>Only ${M.explicit_confirm} of ${M.judgeable} judgeable products (${(M.explicit_confirm/M.judgeable*100).toFixed(0)}%)
  have even one buyer explicitly saying it does the job it was sold to do.</b> Across
  ${num(M.pos_reviews)} positive reviews, “does what it says / delivers on its promise / works as
  advertised” appears ${num(dp.n)} times (${dp.pct}%) — while “easy to use” appears ${num(es.n)}
  times (${es.pct}%). Buyers overwhelmingly praise the <em>experience</em> of the product rather
  than confirming the <em>outcome</em> it promised.</div>
 <div class="note"><b>${M.anticipatory_pct}% of positive reviews are anticipatory</b> — written before
  real use (“just purchased”, “can’t wait to try”, “so far so good”). A 5-star rating is therefore a
  weaker signal of delivered value than it looks. Only
  ${P.filter(p=>(p.fulfillment.anticipatory_pct||0)>=25).length} products have ≥25% of their positive
  reviews in this state.</div>
 <div class="note"><b>Where products fail, they mostly fail at the promise, not the service.</b>
  Among the ${P.filter(p=>p.neg_reviews_analyzed>=5&&p.fulfillment.promise_fail_pct!=null).length}
  products with ≥5 analysed negative reviews, the median share of complaints aimed at the
  <em>core promise</em> (missing feature / broken / deal devalued) is
  <b>${M.promise_fail_median}%</b> — the rest target delivery (support, refunds, UI, setup, limits).</div>`;
tbl($('#bestTable'),['Product','Satisfaction','Explicit “does the job”','Anticipatory','Reviews','Codes','The promise'],
 P.filter(p=>p.fulfillment.reviews_total>=10&&p.fulfillment.satisfaction_rate>=95
   &&p.fulfillment.explicit_delivers>=3)
  .sort((a,b)=>b.fulfillment.explicit_delivers-a.fulfillment.explicit_delivers||
                b.fulfillment.reviews_total-a.fulfillment.reviews_total).slice(0,18)
  .map(p=>[esc(p.name),p.fulfillment.satisfaction_rate.toFixed(1)+'%',
   p.fulfillment.explicit_delivers,
   p.fulfillment.anticipatory_pct!=null?p.fulfillment.anticipatory_pct.toFixed(0)+'%':'—',
   num(p.fulfillment.reviews_total),p.sold_estimate?num(p.sold_estimate):'—',
   esc(p.promise.value_prop||p.promise.subheader||p.tagline||'—')]));
tbl($('#failTable'),['Product','Promise-focused complaints','Satisfaction','Neg. read','The promise','Top complaint'],
 P.filter(p=>p.neg_reviews_analyzed>=5&&p.fulfillment.promise_fail_pct!=null)
  .sort((a,b)=>b.fulfillment.promise_fail_pct-a.fulfillment.promise_fail_pct||
                b.neg_reviews_analyzed-a.neg_reviews_analyzed).slice(0,18)
  .map(p=>[esc(p.name),p.fulfillment.promise_fail_pct+'%',
   p.fulfillment.satisfaction_rate.toFixed(1)+'%',num(p.neg_reviews_analyzed),
   esc(p.promise.value_prop||p.promise.subheader||p.tagline||'—'),
   (p.pain_themes||[]).length?esc(D.pain_labels[p.pain_themes[0].theme]||p.pain_themes[0].theme):'—']));

// ---------- summary tab header + numbers at a glance
$('#sProds').textContent=M.products;
$('#sRevText').textContent=num(M.neg_reviews+M.pos_reviews);
$('#sUnits').textContent=num(M.paid_codes)+' paid';
$('#sUnitsAll').textContent=num(M.coded_units);
$('#sCamp').textContent=M.campaigns.campaigns_total;
tbl($('#glanceTable'),['Metric','Value'],[
 ['Live products',num(M.products)+' across 27 categories'],
 ['License codes issued',num(M.coded_units)+' total = '+num(M.paid_codes)+' paid ('+M.paid_campaigns+
   ' products) + '+num(M.free_codes)+' free lead magnets'],
 ['Gross revenue (point est.)',money(M.gross_rev_point)+' — range '+money(M.gross_rev_floor)+'–'+
   money(M.gross_rev_ceiling)+'. Gross marketplace take, <b>not</b> vendor net'],
 ['Median campaign age',num(M.median_days_live)+' days — evergreen deals, not flash sales'],
 ['Promotional campaigns',M.campaigns.campaigns_total+' distinct ('+M.campaigns.year_range[0]+'–'+
   M.campaigns.year_range[1]+'), on '+M.campaigns.products_with_history+'/342 products'],
 ['Median codes per product',num(1372)+' — vs top 5 products ≈ 20% of all volume'],
 ['Median price / discount','$59 / 75% off'],
 ['Ceiling multiple (top tier ÷ entry)','median '+D.ratio_median+'× · max '+D.ratio_max+'×'],
 ['Ladder architecture',D.ladder_shapes.linear+' linear (agency stacking) vs '+
   D.ladder_shapes.progressive+' progressive (size segmentation)'],
 ['Median satisfaction','<b>'+M.sat_median+'%</b> of reviews are 4–5★ ('+M.judgeable+' products with ≥10 reviews)'],
 ['Buyers confirming the promised job','only '+dp.pct+'% of positive reviews say so'],
 ['Anticipatory (pre-use) 5★ reviews',(D.pos_themes.find(t=>t.k==='anticipatory')||{pct:0}).pct+'%'],
 ['Top complaint','missing feature / promise gap — '+
   (D.pain_themes.find(t=>t.k==='feature_gap')||{pct:0}).pct+'% of negative reviews'],
 ['Refund language',(D.pain_themes.find(t=>t.k==='refund_friction')||{pct:0}).pct+'% of negative reviews'],
 ['Products with a contradicted claim',M.xref_products+' of 342, across '+num(M.xref_reviews)+' reviews'],
 ['Worst-failing claim','“easy / simple / seamless” — 33% of products making it are contradicted'],
 ['Best-holding claim','“lifetime access” — only 2% contradicted'],
 ['Deal devaluation complaints',(D.pain_themes.find(t=>t.k==='deal_devalued')||{pct:0}).pct+
   '% — anger at AppSumo’s own repricing'],
].map(([k,v])=>[esc(k),v]));

// ---------- claims vs complaints tab
$('#xrN').textContent=M.xref_products; $('#xrR').textContent=num(M.xref_reviews);
$('#xrM').textContent=M.xref_mismatch_stated;
const XR=D.xref_rows, ARCH=D.xref_arch;
const XRMAP={}; XR.forEach(r=>{XRMAP[r.deal_id]=r;});
(function(){
  const max=Math.max(...ARCH.map(a=>a.contradiction_rate||0));
  $('#archChart').innerHTML=ARCH.map(a=>{
    const r=a.contradiction_rate||0;
    const col=r>=25?'var(--rose)':r>=10?'var(--orange)':'var(--blue)';
    return `<div class="barrow"><div class="barlab">${esc(a.label.replace(/[“”]/g,''))}</div>
     <button class="barwrap" data-k="${a.k}" title="click for the verbatim pairs">
       <div class="bar" style="width:${(r/max*100).toFixed(1)}%;background:${col}"></div></button>
     <div class="barval">${r.toFixed(0)}% · ${a.contradicted}/${a.claims}</div></div>`;}).join('');
  $('#archChart').querySelectorAll('button.barwrap').forEach(b=>b.onclick=()=>{
    const k=b.dataset.k, host=$('#archChart');
    const ex=host.parentElement.querySelector('.qbox'); if(ex){ex.remove();return;}
    const rows=XR.filter(r=>r.claims.some(c=>c.k===k));
    const d=document.createElement('div'); d.className='qbox';
    d.innerHTML=`<h3 style="margin-top:14px">${esc((ARCH.find(a=>a.k===k)||{}).label)} —
      ${rows.length} products contradicted <span class="barval">(showing up to 8)</span></h3>`+
     (rows.slice(0,8).map(r=>{
       const c=r.claims.find(c=>c.k===k), e=(c.ex||[])[0]||{};
       return `<div class="pair"><div class="cl"><b>${esc(r.name)}</b> promised
         ${c.promised?'“…'+esc(c.promised.slice(-110))+'…”':'this'}</div>
         <div class="cm">${esc(e.ctx||'')}<span class="who">${e.star||'?'}★ · ${e.up||0} found helpful ·
         matched “${esc(e.matched||'')}” · ${c.n} such review${c.n>1?'s':''}</span></div></div>`;}).join('')
       || '<p class="sub">No products matched.</p>');
    host.parentElement.appendChild(d);
  });
})();
const xa=$('#xArch');
ARCH.forEach(a=>xa.add(new Option(a.label.replace(/[“”]/g,'')+' ('+a.contradiction_rate+'%)',a.k)));
const XSORT={n:r=>-r.n,rev:r=>-r.claims.reduce((s,c)=>s+c.n,0),sat:r=>r.satisfaction??999,
  neg:r=>-r.neg_reviews,sold:r=>-(r.sold_estimate??-1)};
function xcard(r){
  const pill=n=>n>=5?'hi':n>=3?'md':'lo';
  return `<details class="xr" id="x${r.deal_id}"><summary class="xrh" style="list-style:none">
    <div><div class="pname">${esc(r.name)} <span class="pill ${pill(r.n)}">${r.n} claim${r.n>1?'s':''} contradicted</span></div>
      <div class="ptag">${esc(r.promise.value_prop||r.promise.subheader||'')}</div>
      <div style="margin-top:5px">${r.claims.map(c=>`<span class="tag r">${esc(c.label.replace(/[“”]/g,''))} ${c.n}</span>`).join('')}</div></div>
    <div class="pnums"><div><b>${r.satisfaction!=null?r.satisfaction.toFixed(0)+'%':'—'}</b><span>satisfaction</span></div>
      <div><b>${num(r.review_count)}</b><span>reviews</span></div>
      <div><b>${r.sold_estimate?num(r.sold_estimate):'—'}</b><span>codes</span></div></div>
    </summary><div class="xrb">${r.claims.map(c=>`
      <h3 style="margin-top:14px">${esc(c.label)} <span class="barval">— ${c.n} contradicting review${c.n>1?'s':''}</span></h3>
      <div class="pair"><div class="cl"><b>Promised:</b> ${c.promised?'…'+esc(c.promised):'<span class="barval">buyer states listing ≠ product</span>'}</div>
      ${c.ex.map(e=>`<div class="cm">${esc(e.ctx||'')}<span class="who">${e.star}★ · ${e.up||0} found helpful ·
        trigger “${esc(e.matched)}” · <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a></span></div>`).join('')}</div>`).join('')}
      <div class="barval" style="margin-top:9px">Category: ${esc(r.category||'—')} · ${r.neg_reviews} negative reviews read</div>
    </div></details>`;
}
function xrender(){
  const k=xa.value, s=$('#xSort').value;
  let r=XR.filter(x=>!k||x.claims.some(c=>c.k===k));
  r.sort((a,b)=>XSORT[s](a)-XSORT[s](b));
  $('#xCount').textContent=r.length+' products';
  $('#xList').innerHTML=r.length?r.map(xcard).join(''):'<div class="empty">None.</div>';
}
xa.onchange=xrender; $('#xSort').onchange=xrender; xrender();

// ---------- campaigns tab (participation history; economics are rendered server-side
// by campaigns_section.render() into #campBody)
const CP=M.campaigns;
$('#cN').textContent=CP.campaigns_total;
$('#cY').textContent=CP.year_range[0]+'–'+CP.year_range[1];
$('#cP').textContent=CP.products_with_history+'/342';
$('#d0').textContent=num((CP.depth.find(d=>d.band==='1')||{}).med_units);
$('#d24').textContent=num((CP.depth.find(d=>d.band==='24+')||{}).med_units);
(function(){
  const max=Math.max(...CP.kind_rows.map(k=>k.products));
  $('#kindChart').innerHTML=CP.kind_rows.map(k=>
   `<div class="barrow"><div class="barlab">${esc(k.label)}</div>
    <div class="barwrap"><div class="bar" style="width:${(k.products/max*100).toFixed(1)}%"></div></div>
    <div class="barval">${k.products} products · ${k.distinct} runs</div></div>`).join('');
})();
tbl($('#campTable'),['Campaign','Type','Products','Years run'],
 CP.top_campaigns.slice(0,16).map(c=>[esc(c.slug),esc(c.kind),num(c.products),
  c.years.length?c.years[0]+(c.years.length>1?'–'+c.years[c.years.length-1]:''):'—']));
$('#gaEaNote').innerHTML=`<b>Extended access is table stakes, not a perk.</b> ${CP.ga_ea.both} products
 appear in <em>both</em> the general-access and extended-access audiences of the same campaign,
 ${CP.ga_ea.ga_only} are general-access only and ${CP.ga_ea.ea_only} extended-only. Don't plan a
 launch around getting extended access — assume you'll be in both or neither.`;
tbl($('#depthTable'),['Campaigns','n','Med. codes','Med. sat','Med. reviews','% free'],
 CP.depth.map(d=>[d.band,d.n,d.med_units!=null?num(d.med_units):'—',
  d.med_sat!=null?d.med_sat+'%':'—',num(d.med_reviews),d.pct_free+'%']));
tbl($('#tenureTable'),['Cohort','n','Low-promo codes','High-promo codes','Low sat','High sat','Sat gap'],
 CP.tenure.map(t=>[t.year,t.n,t.lo_units!=null?num(t.lo_units):'—',t.hi_units!=null?num(t.hi_units):'—',
  t.lo_sat!=null?t.lo_sat+'%':'—',t.hi_sat!=null?t.hi_sat+'%':'—',
  (t.sat_gap>0?'−':'')+Math.abs(t.sat_gap||0)+' pts']));
const satDrop=CP.tenure.filter(t=>(t.sat_gap||0)>0).length;
$('#tenureNote').innerHTML=`<b>The volume story collapses under the control, the satisfaction story
 does not.</b> Within-cohort, high-promotion products beat low-promotion on median codes in only
 ${CP.tenure.filter(t=>(t.hi_units||0)>(t.lo_units||0)).length} of ${CP.tenure.length} cohorts —
 no consistent effect. But satisfaction is lower for heavily-promoted products in
 <b>${satDrop} of ${CP.tenure.length}</b> cohorts, and the gap widens for newer launches
 (1.0 pt in 2021 → 5.3 pts in 2026). Promotion depth is a proxy for how long you've been listed,
 not a lever you can pull for sales.`;
tbl($('#mixTable'),['Promotion depth','Products','Neg. reviews','Deal devalued','Refund language','Feature gap','Broken'],
 CP.complaint_mix.map(c=>[esc(c.band),c.n,num(c.neg),c.deal_devalued+'%',c.refund_friction+'%',
  c.feature_gap+'%',c.broken+'%']));
$('#mixNote').innerHTML=`<b>Counterintuitive and actionable:</b> "deal devalued" anger is
 <b>${CP.complaint_mix[0].deal_devalued}%</b> of negatives for lightly-promoted products (0–5
 campaigns) versus <b>${CP.complaint_mix[CP.complaint_mix.length-1].deal_devalued}%</b> for the
 always-on roster. Refund language follows the same gradient
 (${CP.complaint_mix[0].refund_friction}% → ${CP.complaint_mix[CP.complaint_mix.length-1].refund_friction}%).
 If your product is <em>not</em> in every sale, the buyers who paid more feel shortchanged when it
 later appears discounted. Being perpetually on promotion is, perversely, what keeps existing
 buyers from feeling cheated.`;
tbl($('#alwaysTable'),['Product','Codes','Entry','Satisfaction','Reviews','Claims broken'],
 CP.always_on.slice(0,16).map(a=>[esc(a.name),num(a.units),a.is_free?'FREE':money(a.entry_price),
  a.satisfaction!=null?a.satisfaction+'%':'—',num(a.reviews),a.contradicted||'0']));
$('#recentSub').textContent=`${CP.recent.n} products first promoted in 2025–2026. Only `+
 `${CP.recent.with_codes} publish inventory yet, so treat these as early signals. Median entry `+
 `$${CP.recent.med_entry}, median satisfaction ${CP.recent.med_sat}%, ${CP.recent.contradicted} already have a contradicted claim.`;
tbl($('#recentTable'),['Product','Codes','Entry','Satisfaction','Reviews','Campaigns','Claims broken'],
 CP.recent.rows.slice(0,14).map(r=>[esc(r.name),r.units?num(r.units):'—',
  r.entry_price?money(r.entry_price):'FREE',r.satisfaction!=null?r.satisfaction+'%':'—',
  num(r.reviews),r.campaigns,r.contradicted||'0']));

// ---------- method tables
tbl($('#srcTable'),['Pass','Source','Records','What it gave'],[
 ['1','<code>/api/v2/deals/esbrowse/</code> × 27 categories','342 products','catalog, price, rating, taxonomy, <code>active_codes</code>'],
 ['2','<code>/api/v2/deals/&lt;id&gt;/</code> × 342','342 / 342','feature×tier matrix, star breakdown, plan terms'],
 ['3','<code>/products/&lt;slug&gt;/</code> <code>__NEXT_DATA__</code> × 342','342 / 342','full tier ladders (1,057 plan rows = 1,048 sellable + 9 Plus) — absent from the API'],
 ['4','<code>/api/v2/deals/&lt;id&gt;/reviews/?rating=N</code>','7,405 reviews','verbatim 1–3★ text + 20 most-recent'],
 ['5','<code>/api/v2/deals/&lt;id&gt;/reviews/?rating=4,5</code>','5,819 reviews','verbatim 4–5★ text (sampled — see caveats)'],
 ['6','<code>/api/v2/deals/&lt;id&gt;/questions/</code>',num(M.questions)+' read','pre-purchase questions'],
 ['7','esbrowse <code>story_details</code> / <code>story_highlights</code>','342 products',"the vendor's own stated promise"],
 ['8','<code>/products/&lt;slug&gt;/</code> <code>story.html_body</code>, <code>faqs</code>, <code>overview_media</code>','342 / 342','full listing copy — 1.6M chars of claim text, median ~4,000/product'],
 ['9','<code>crossref.py</code> — 13 claim archetypes','101 products','promise → complaint pairs with verbatim evidence'],
 ['10','<code>campaigns.py</code> — per-tier price-per-code from pass 3','203 campaigns','lifetime codes sold, gross revenue floor–ceiling, campaign age/velocity, contractual terms']]);
$('#covBox').innerHTML=`
 <div class="note ok"><b>Catalogue:</b> 342/342 live deals reconciled against AppSumo's own site-wide
  count. Every product's embedded taxonomy agrees with the category it was fetched under (0 mismatches).
  Categories form a strict partition — 0 products appear in more than one.</div>
 <div class="note ok"><b>Reviews:</b> ${num(M.neg_reviews)} of ${num(M.neg_expected)} expected 1–3★ reviews captured
  (${(M.neg_reviews/M.neg_expected*100).toFixed(1)}%). ${M.capped_products} products have a rating bucket above the
  API's hard 20-record cap, so their negative set is partial.</div>
 <div class="note"><b>Sales volume:</b> derived for ${sold.length} products via <code>active_codes − codes_remaining</code>.
  Validated on 6 freebies against AppSumo's published download counts: median error 0.3%, worst 1.7%.
  ${nc.length} products use no code system and have <b>no</b> volume estimate — they are never mixed into the same ranking.</div>`;
$('#cavBox').innerHTML=`
 <div class="note"><b>1. Units sold are derived, not published.</b> No revenue or units field exists.
  The codes arithmetic validated at 0.3% median error on freebies, but freebies are the only place it
  could be checked. Treat paid-product figures as estimates.</div>
 <div class="note"><b>2. Revenue is a floor.</b> <code>est. revenue</code> = units × <i>entry-tier</i> price.
  Buyers who stacked to tier 2–10 paid more, so true revenue is higher by an unmeasurable margin.
  AppSumo's cut is not deducted.</div>
 <div class="note"><b>3. Theme counts are mentions, not complaints.</b> Regex tagging over review text.
  A review can trip several themes; a keyword can land in a positive clause inside a negative review.
  Every quote shows the exact token that triggered it so you can judge the call yourself.</div>
 <div class="note"><b>4. Questions are capped at 20 per product</b> (most recent), out of
  ${num(M.questions_total_available)} on site — ${num(M.questions)} read, i.e.
  ${(M.questions/M.questions_total_available*100).toFixed(0)}%. Skews toward recently-asked.</div>
 <div class="note"><b>4b. Positive review TEXT is a 26% sample; satisfaction RATES are exact.</b>
  The API caps every rating bucket at 20 records. Negatives are rare so coverage is high
  (${(M.neg_reviews/M.neg_expected*100).toFixed(0)}% of all 1–3★ reviews), but 5★ reviews are not:
  only ${num(M.pos_reviews)} of ${num(M.pos_expected)} (${(M.pos_reviews/M.pos_expected*100).toFixed(0)}%)
  were readable, and 165 products are capped. So <b>praise-theme percentages describe a sample of
  recent positive reviews</b>, while satisfaction rates come from AppSumo's complete star counts and
  are exact for all 342.</div>
 <div class="note"><b>5. Plus-exclusive variants are separate listings sharing the parent's reviews.</b>
  Screpy / Screpy-Plus return byte-identical review sets. Any "best-reviewed" ranking double-counts them;
  filter by name prefix to collapse.</div>
 <div class="note"><b>5b. Contradiction rates are floors, not measurements.</b> A contradiction is
  only detected when the reviewer happens to use language the archetype pattern catches, so the true
  rates are higher than shown. Counts are per-product "was this claim contradicted at least once",
  not "what share of buyers noticed". ${M.boilerplate_filtered} AppSumo boilerplate plan-term strings
  were filtered out of claim detection, and Switchy's FAQs are excluded because they belong to a
  different product (see Summary → Confidence).</div>
 <div class="note"><b>6. Snapshot, not a time series.</b> Prices, stock and codes move constantly.
  Everything here is 2026-10-26.</div>`;

// ---------- browse
const gsel=$('#fGroup'), csel=$('#fCat');
[...new Set(P.map(p=>p.group||'(uncategorized)'))].sort().forEach(g=>gsel.add(new Option(g,g)));
function fillCats(){
  const g=gsel.value; csel.length=1;
  [...new Set(P.filter(p=>!g||(p.group||'(uncategorized)')===g).map(p=>p.category).filter(Boolean))].sort()
   .forEach(c=>csel.add(new Option(c,c)));
}
fillCats(); gsel.onchange=()=>{fillCats();render()};

function match(p,q){
  if(!q) return true;
  const hay=[p.name,p.tagline,p.category,p.subcategory,p.group,p.alternative_to,p.best_for,
   p.review_summary,(p.core_features||[]).map(f=>f.feature+' '+(f.tooltip||'')).join(' '),
   (p.common_features||[]).join(' '),(p.plan_terms||[]).join(' '),
   (p.feature_matrix||[]).map(f=>f.feature).join(' '),
   (p.pain_themes||[]).map(t=>D.pain_labels[t.theme]).join(' '),
   (p.pos_themes||[]).map(t=>D.pos_labels[t.theme]).join(' '),
   (p.promise||{}).value_prop,(p.promise||{}).subheader,
   ((p.promise||{}).highlights||[]).join(' '),((p.promise||{}).serves||[]).join(' ')
   ].join(' ').toLowerCase();
  return q.toLowerCase().split(/\\s+/).filter(Boolean).every(w=>hay.includes(w));
}
// Paid units and free downloads are NOT the same quantity - a freebie's 66k
// downloads would otherwise outrank every real sale. Keep them in separate sorts.
const u=(p,m)=>(p.sales_method===m&&p.sold_estimate)?p.sold_estimate:-1;
const SORT={sold:p=>-u(p,'codes'),dl:p=>-u(p,'downloads'),rev:p=>-(p.est_revenue_at_entry??-1),
 reviews:p=>-(p.review_count||0),rating:p=>-(p.rating||0),entry:p=>p.entry_price??1e9,
 top:p=>-(p.top_price||0),wtp:p=>-(p.wtp_ratio||0),disc:p=>-(p.discount_pct||0),
 neg:p=>-(p.neg_reviews_analyzed||0),
 sat:p=>-((p.fulfillment||{}).satisfaction_rate??-1),
 explicit:p=>-((p.fulfillment||{}).explicit_delivers??-1),
 antic:p=>-((p.fulfillment||{}).anticipatory_pct??-1),
 pf:p=>-((p.fulfillment||{}).promise_fail_pct??-1),
 claims:p=>-((XRMAP[p.deal_id]||{}).n??-1),
 name:p=>(p.name||'').toLowerCase()};
let open_=new Set();
function render(){
  const q=$('#q').value.trim(), g=gsel.value, c=csel.value, l=$('#fList').value,
        mr=parseFloat($('#fRating').value)||0, mp=parseFloat($('#fPrice').value)||Infinity,
        hs=$('#fSold').checked, s=$('#fSort').value;
  let r=P.filter(p=>match(p,q)&&(!g||(p.group||'(uncategorized)')===g)&&(!c||p.category===c)
    &&(!l||p.listing===l)&&(p.rating||0)>=mr&&(p.entry_price??0)<=mp&&(!hs||p.sold_estimate));
  r.sort((a,b)=>{const x=SORT[s](a),y=SORT[s](b);return typeof x==='string'?x.localeCompare(y):x-y});
  $('#count').textContent=r.length+' of '+P.length+' products';
  $('#list').innerHTML=r.length?r.map(card).join(''):'<div class="empty">No products match those filters.</div>';
  r.forEach(p=>{if(open_.has(p.deal_id)){const e=document.getElementById('p'+p.deal_id);if(e)e.open=true;}});
  $('#list').querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{
    const id=+d.id.slice(1); d.open?open_.add(id):open_.delete(id);}));
}
function card(p){
  const sold=p.sales_method==='codes'?`<b>${num(p.sold_estimate)}</b><span>units sold</span>`
    :p.sales_method==='downloads'?`<b>${num(p.sold_estimate)}</b><span>free downloads</span>`
    :`<b>${num(p.review_count)}</b><span>reviews · no sales data</span>`;
  return `<details class="prod" id="p${p.deal_id}"><summary class="phead" style="list-style:none">
   <div><div class="pname">${esc(p.name)} ${p.is_free?'<span class="tag g">FREE</span>':''}
     ${p.listing==='Marketplace'?'<span class="tag o">Marketplace</span>':'<span class="tag b">Select</span>'}</div>
     <div class="ptag">${esc(p.tagline||'')}</div>
     <div style="margin-top:6px"><span class="tag">${esc(p.group||'')}</span><span class="tag">${esc(p.category||'')}</span>
     ${p.subcategory?`<span class="tag">${esc(p.subcategory)}</span>`:''}</div></div>
   <div class="pnums"><div>${sold}</div>
     <div><b>${p.entry_price?money(p.entry_price):'—'}</b><span>entry${p.wtp_ratio?' → '+money(p.top_price):''}</span></div>
     <div><b>${p.rating?Number(p.rating).toFixed(2):'—'}</b><span>${num(p.review_count)} reviews</span></div></div>
   </summary><div class="pbody">${body(p)}</div></details>`;
}
function body(p){
  const lad=(p.ladder||[]).length?`<h3>Price ladder — ${esc(p.ladder_shape||'n/a')}
     ${p.wtp_ratio?'· '+p.wtp_ratio+'× ceiling':''}</h3><table class="fm"><thead><tr><th>Tier</th>
     <th class="num">Deal</th><th class="num">Regular</th><th>Type</th></tr></thead><tbody>${
     p.ladder.map(t=>`<tr><td>T${esc(t.tier)}</td><td class="num">${money(t.price)}</td>
      <td class="num">${t.original?money(t.original):'—'}</td><td>${esc(t.plan_type||'')}</td></tr>`).join('')}</tbody></table>`:'';
  const fm=(p.feature_matrix||[]).length?`<h3>Feature × tier limits</h3><div style="overflow-x:auto">
    <table class="fm"><thead><tr><th>Feature</th>${[...new Set((p.feature_matrix||[]).flatMap(f=>Object.keys(f.by_tier||{})))]
      .sort((a,b)=>a-b).map(t=>`<th class="num">T${esc(t)}</th>`).join('')}</tr></thead><tbody>${
      p.feature_matrix.map(f=>`<tr><td>${esc(f.feature)}${f.tooltip?` <span class="barval" title="${esc(f.tooltip)}">ⓘ</span>`:''}</td>${
        [...new Set(p.feature_matrix.flatMap(x=>Object.keys(x.by_tier||{})))].sort((a,b)=>a-b)
        .map(t=>`<td class="num">${esc((f.by_tier||{})[t]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'';
  const feats=(p.core_features||[]).length?`<h3>Core features</h3><ul class="feat">${p.core_features.map(f=>
    `<li><b>${esc(f.feature)}</b>${f.tooltip?` — <span class="barval">${esc(f.tooltip)}</span>`:''}</li>`).join('')}</ul>`:'';
  const com=(p.common_features||[]).length?`<h3>Included</h3><div>${p.common_features.map(f=>`<span class="tag">${esc(f)}</span>`).join('')}</div>`:'';
  const terms=(p.plan_terms||[]).length?`<h3>Plan terms</h3><ul class="feat">${p.plan_terms.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:'';
  const pains=(p.pain_themes||[]).length?`<h3>Painpoints <span class="barval">(${p.neg_reviews_analyzed} of ${p.neg_reviews_expected} negative reviews read)</span></h3>
    <div>${p.pain_themes.map(t=>`<span class="tag r">${esc(D.pain_labels[t.theme]||t.theme)} ${t.n}</span>`).join('')}</div>`:'';
  const quotes=(p.pain_quotes||[]).length?`<h3>What customers said</h3>${p.pain_quotes.map(q=>
    `<div class="q">${esc(q.ctx||q.text)}<span class="who">${q.star}★ · ${q.up||0} helpful ·
     ${q.theme&&q.theme!=='_untagged'?'“'+esc(q.matched)+'” → '+esc(D.pain_labels[q.theme]||q.theme):'untagged'}</span></div>`).join('')}`:'';
  const qs=(p.questions_sample||[]).length?`<h3>Pre-purchase questions <span class="barval">(${p.questions_sampled} of ${num(p.questions_total)} read)</span></h3>
    ${p.questions_sample.map(q=>`<div class="q">${esc(q)}</div>`).join('')}`:'';
  const alt=p.alternative_to?`<h3>Positioned against</h3><div>${p.alternative_to.split(', ').map(a=>`<span class="tag b">${esc(a)}</span>`).join('')}</div>`:'';
  const meta=`<h3>Signals</h3><div style="font-size:12.6px">
    ${p.sold_estimate?`<b>${num(p.sold_estimate)}</b> units (${p.sales_method}) · est. <b>${money(p.est_revenue_at_entry)}</b> at entry price<br>`:''}
    ${p.active_codes?`codes issued ${num(p.active_codes)} · remaining ${num(p.codes_remaining)}<br>`:''}
    rating ${stars(p.rating)} · ${num(p.review_count)} reviews · ${num(p.comment_count)} comments<br>
    ${p.availability?'availability: '+esc(p.availability)+' · ':''}${p.refundable_days?p.refundable_days+'-day refund · ':''}
    launched ${esc(p.start_date||'?')}<br>
    <a href="${esc(p.url)}" target="_blank" rel="noopener">AppSumo listing</a>${p.product_url?` · <a href="${esc(p.product_url)}" target="_blank" rel="noopener">vendor site</a>`:''}</div>`;
  const pr=p.promise||{}, f=p.fulfillment||{};
  const promise=(pr.value_prop||pr.subheader||pr.highlights?.length)?`<h3>What it purports to serve</h3>
    <div style="font-size:12.8px">${pr.value_prop?`<div><b>${esc(pr.value_prop)}</b></div>`:''}
    ${pr.subheader?`<div class="barval" style="margin:3px 0 6px">${esc(pr.subheader)}</div>`:''}
    ${(pr.highlights||[]).length?`<ul class="feat">${pr.highlights.slice(0,6).map(h=>`<li>${esc(h)}</li>`).join('')}</ul>`:''}
    ${(pr.serves||[]).length?`<div style="margin-top:5px"><span class="barval">for:</span> ${pr.serves.map(s=>`<span class="tag g">${esc(s)}</span>`).join('')}</div>`:''}
    ${(pr.replaces||[]).length?`<div style="margin-top:3px"><span class="barval">positioned against:</span> ${pr.replaces.map(s=>`<span class="tag b">${esc(s)}</span>`).join('')}</div>`:''}</div>`:'';
  const verdict=f.reviews_total?`<h3>Promise vs delivery</h3><div style="font-size:12.8px">
    <div><b>${f.satisfaction_rate!=null?f.satisfaction_rate.toFixed(1)+'%':'—'}</b> of ${num(f.reviews_total)} reviews are 4–5★
      <span class="barval">(exact — from AppSumo's full star counts)</span></div>
    <div>${f.stars_1_2_pct!=null?f.stars_1_2_pct.toFixed(1)+'%':'—'} are 1–2★ · star split
      ${[5,4,3,2,1].map(k=>`${k}★:${num((p.stars||{})[k]||0)}`).join(' · ')}</div>
    <div style="margin-top:5px">Buyers explicitly confirming the promised job:
      <b>${f.explicit_delivers||0}</b>${f.pos_analyzed?` of ${f.pos_analyzed} positive reviews read`:''}</div>
    <div>Anticipatory (pre-use) praise: <b>${f.anticipatory_pct!=null?f.anticipatory_pct.toFixed(0)+'%':'—'}</b>
      · praise with an explicit caveat: <b>${f.qualified_pct!=null?f.qualified_pct.toFixed(0)+'%':'—'}</b></div>
    <div>Negative complaints aimed at the core promise: <b>${f.promise_fail_pct!=null?f.promise_fail_pct+'%':'—'}</b>
      <span class="barval">(vs delivery: support/refunds/UI/setup/limits)</span></div>
    ${f.pos_coverage_pct!=null&&f.pos_coverage_pct<99?`<div class="barval" style="margin-top:4px">positive text is a ${f.pos_coverage_pct.toFixed(0)}% sample — API caps each rating bucket at 20</div>`:''}
    </div>`:'';
  const xc=XRMAP[p.deal_id];
  const xsec=xc?`<h3>Claims contradicted by buyers <span class="pill ${xc.n>=5?'hi':xc.n>=3?'md':'lo'}">${xc.n}</span></h3>
    ${xc.claims.map(c=>`<div class="pair"><div class="cl"><b>${esc(c.label.replace(/[“”]/g,''))}</b>
      ${c.promised?'— promised “…'+esc(c.promised.slice(-100))+'…”':''}
      <span class="barval">· ${c.n} review${c.n>1?'s':''}</span></div>
      ${(c.ex||[]).slice(0,2).map(e=>`<div class="cm">${esc(e.ctx||'')}<span class="who">${e.star}★ · ${e.up||0} helpful · trigger “${esc(e.matched)}”</span></div>`).join('')}
      </div>`).join('')}`:'';
  const posq=(p.pos_quotes||[]).length?`<h3>What happy buyers said</h3>${p.pos_quotes.slice(0,5).map(q=>
    `<div class="q" style="border-left-color:var(--green)">${esc(q.ctx||q.text)}<span class="who">${q.star}★ · ${q.up||0} helpful ·
     ${q.theme?esc(D.pos_labels[q.theme]||q.theme):''}${q.matched?' · “'+esc(q.matched)+'”':''}</span></div>`).join('')}`:'';
  const posth=(p.pos_themes||[]).length?`<h3>Praise themes</h3><div>${p.pos_themes.filter(t=>
      t.theme!=='anticipatory'&&t.theme!=='qualified_praise')
      .map(t=>`<span class="tag g">${esc(D.pos_labels[t.theme]||t.theme)} ${t.n}</span>`).join('')}
    ${(p.pos_themes||[]).filter(t=>t.theme==='anticipatory'||t.theme==='qualified_praise')
      .map(t=>`<span class="tag o">${esc(D.pos_labels[t.theme]||t.theme)} ${t.n}</span>`).join('')}</div>`:'';
  const summ=p.review_summary?`<div class="note">${esc(p.review_summary)}</div>`:'';
  const cap=(p.review_fetch_capped||[]).length?`<div class="note">Negative-review set is <b>partial</b>: ${
    p.review_fetch_capped.map(c=>c.rating+'★ '+c.returned+'/'+c.expected).join(', ')} (API caps at 20).</div>`:'';
  return `<div><div style="font-size:13px">${esc(p.tagline||'')}</div>${summ}${cap}${promise}${verdict}${xsec}${feats}${com}${fm}${lad}${terms}${alt}${meta}</div>
          <div>${posth}${posq}${pains}${quotes}${qs}</div>`;
}
['q','fList','fSort','fRating','fPrice','fSold'].forEach(id=>{
  const e=$('#'+id); e.addEventListener('input',render); e.addEventListener('change',render);});
render();
})();
</script>
"""

SYNTH = """
<p><strong>Volume is wildly concentrated.</strong> Across the 174 products with a derivable
signal, 622,571 units sold — but the median is 1,372 while the top five account for a fifth of
it. WordHero (~34,875 units at $89, ≈$3.1M) and Reoon Email Verifier (~26,197 at $79, ≈$2.1M)
are the revenue leaders. The single biggest mover, ApproveMe's contract-template library
(~51,311), is a <em>free</em> lead magnet — the highest-volume items on AppSumo are frequently
not for sale at all.</p>

<p><strong>The winning pattern is unglamorous.</strong> The top sellers are not AI frontier tools.
They are link-in-bio (Switchy, 43k), AI content writing (WordHero, 35k), email verification
(Reoon, 26k), business-education courses (27k), and spreadsheet/template packs. Every one removes
a recurring manual chore at a price under $90. The AI-branded products that sold well are AI
<em>applied to an existing chore</em> — writing, verification, transcription — not AI as the product.</p>

<p><strong>Willingness to pay is a stacking game, not a value estimate.</strong> The median
top-tier is 5× entry, but 20 products run a 10-tier <em>linear</em> ladder at exactly 10×
($79 → $790, $89 → $890). Linear ladders mean marginal willingness to pay is flat: the buyer is
an agency purchasing N identical codes, not a larger company paying for more capability. That is a
distribution channel, not a pricing strategy. Progressive ladders (89 products) are the ones
actually segmenting by buyer size — and ResumeUp.AI's $49 → $2,999 spread (61×) shows how far the
ceiling can be pushed when the entry price is treated purely as a tripwire.</p>

<p><strong>Ceiling price is not evidence of revenue.</strong> LeadOcean lists a $1,999 top tier
against 1 derived unit sold. High ceilings with no volume are aspiration; the 10× linear ladders
with 4,000+ units (FlipLink.me, XInterview AI) are the real money.</p>

<p><strong>The painpoints are delivery failures, not feature requests.</strong> The top four
themes — missing feature / promise gap (19.6%), broken (18.5%), refund sought (17.5%), and limits
too tight (17.2%) — are all about the gap between what the listing promised and what arrived.
Support unresponsive is only 6.9%, but it co-occurs with refund language constantly: the sequence
in the text is usually <em>product broke → support silent → refund</em>. Refund mentions at 17.5%
of all negative reviews is the single most actionable number here.</p>

<p><strong>Pre-purchase questions reveal where listings fail to answer.</strong> 8.3% ask whether
"lifetime" really means lifetime, 8.1% ask about commercial/client/white-label scope, and 4.6%
explicitly ask how the deal differs from the vendor's public paid plan. Those are all questions the
listing itself should settle. The deal-parity question in particular is a trust signal: buyers
suspect the AppSumo tier is a cut-down version, and several reviews confirm that suspicion
after purchase.</p>

<p><strong>Deal devaluation is AppSumo's own structural risk.</strong> 3.2% of negative reviews
complain that the current offer is worse than an earlier one for the same product — "stripped
things down and still charge more." It is a small share but a distinctive one: it is anger aimed at
the <em>marketplace's</em> repricing, not the vendor's product, and it lands on repeat buyers who
are AppSumo's core audience.</p>

<p><strong>Category signal.</strong> SEO &amp; Analytics generates the most negative reviews (297),
led by refund language. Content Marketing's dominant complaint is limits/credits (56) — the
category is priced on consumption and buyers misjudge the quota. Lead Generation and Project
Management both lead on integration failures, which is what you'd expect for tools whose whole
job is connecting to other systems.</p>
"""

SYNTH2 = """
<p><strong>Headline: satisfaction is high, but corroboration is thin.</strong> Of the 250 products
with enough reviews to judge (≥10), median satisfaction is <strong>89.8%</strong> 4–5★ and 123 sit
at ≥90%. That looks like a market where products deliver. But when you ask the sharper question —
does a buyer actually confirm the product did the job it was sold to do? — only
<strong>165 of 250 (66%)</strong> have <em>even one</em> such review. Across 5,819 positive reviews,
"does what it says / delivers on its promise / works as advertised" appears 366 times
(<strong>6.3%</strong>), while "easy to use / intuitive / straightforward" appears 1,353 times
(<strong>23.3%</strong>) — nearly four times as often.</p>

<p><strong>Buyers review the experience, not the outcome.</strong> The praise hierarchy is
ease (23.3%) → value for price (9.1%) → works reliably (8.1%) → does the promised job (6.3%) →
output quality (6.1%) → beats an alternative (5.7%) → support (5.2%) → saves time (5.2%).
Ease-of-use dominates because it is the only thing a reviewer can assess in the first hour, which
is exactly when most AppSumo reviews are written. <strong>5.7% of positive reviews are explicitly
anticipatory</strong> — "just purchased", "can't wait to try", "so far so good" — and a further
10.3% carry an explicit caveat inside a 4–5★ rating. A five-star score on this marketplace is
weaker evidence of delivered value than it appears.</p>

<p><strong>The lifetime-deal economics are the real product.</strong> "Good value for the price"
(9.1%) plus explicit one-time-payment praise is the second-largest cluster, and the most emotionally
charged reviews are about escaping subscriptions — KillerPlayer's buyer calculates "$1,800… saving
nearly $1,600 by making this one-time purchase." Only 41 reviews describe actually cancelling a
subscription, but the ones that do are the most persuasive writing in the corpus. The job being
hired for is frequently <em>stop paying monthly for X</em>, not <em>do X better</em>.</p>

<p><strong>Support is the swing factor, in both directions.</strong> It appears in 5.2% of positive
reviews and 6.9% of negative ones — but its role is asymmetric. Positive reviews describe
founder-level responsiveness as decisive ("emailed Brian on Saturday and got a response in
10 minutes"; a bug fixed inside 24 hours). Negative reviews describe the sequence
<em>product broke → support silent → refund</em>. DivMagic's 5★ review is the clearest case: the
product visibly failed ("my mobile version was crooked and nothing was working") and the review is
still five stars because support rescued it. Support does not just resolve complaints; it converts
failures into positive reviews.</p>

<p><strong>When products fail, they fail at the promise, not the service.</strong> Among the 143
products with ≥5 analysed negative reviews, the median share of complaints aimed at the
<em>core promise</em> (missing feature / broken / deal devalued) is <strong>42%</strong> — the
majority of the rest target delivery (support, refunds, UI, setup, limits). The distinction
matters commercially: a delivery failure is fixable by the vendor next quarter, whereas a promise
failure means the listing oversold and the refund clock is already running. The worst offenders
combine both — Local Rank Tracker (86% promise-focused complaints, 72.1% satisfaction, $239 entry,
36 negative reviews read) and Kortex (80%, 60.0% satisfaction) are the clearest cases of a listing
writing cheques the product did not cash.</p>

<p><strong>The best-evidenced performers are unglamorous and specific.</strong> Reoon Email Verifier
stands out: 756 reviews, <strong>98.5%</strong> satisfaction, 7 explicit "does the job"
confirmations, only 2.6% anticipatory — and ~26,197 units sold (≈$2.1M). Writecream (633 reviews,
95.9%) and Switchy (276 reviews, 96.7%, ~43,142 units) follow the same shape. The common thread is a
narrow, verifiable promise: "protect your email server's reputation", "boost conversions with
retargeting links". Narrow promises are easy to confirm in one session, which is why they generate
corroborating reviews — and why they convert. The products with the widest promises
("all-in-one", "maximize your sales potential") cluster at the bottom.</p>

<p><strong>Practical read.</strong> If you are buying: weight explicit job-confirmation and low
anticipatory share above the star rating, and treat a 4.6★ with 200 reviews as weaker evidence than
a 4.9★ whose reviewers name the outcome. If you are selling here: a narrow, one-session-verifiable
promise outperforms an expansive one, because it produces reviews that corroborate rather than
anticipate — and because promise-focused complaints are the kind that end in refunds.</p>
"""

SYNTH3 = """
<p><strong>The method matters more than the count.</strong> A contradiction is only recorded against a
product that <em>actually made that claim</em>. Promise text is the union of two sources, because
neither alone works: the structured feature lists carry "Unlimited chat" and "Unlimited domains",
while the long-form listing copy and vendor FAQs carry "white-label", "24/7 support" and "as many as
you want". Using only the marketing copy dropped "unlimited" detection from 113 products to 54. Using
only the feature lists missed white-label almost entirely.</p>

<p><strong>Claim hardness predicts claim survival.</strong> Order the archetypes by how checkable they
are and the contradiction rates fall out in the same order. Hard, falsifiable promises hold:
lifetime access <strong>2%</strong> contradicted (6 of 312), automation 2% (4 of 184), white-label 1%
(1 of 90). Soft adjectives fail: easy/simple/seamless <strong>33%</strong> (50 of 153), all-in-one
<strong>29%</strong> (14 of 49), 24/7-or-responsive support <strong>32%</strong> (6 of 19). The
middle tier — unlimited 14%, free 11%, in-minutes 9%, AI-powered 8% — sits where the claim is
specific but the buyer's expectation of "enough" is not.</p>

<p><strong>"Easy" is the most dangerous word on the marketplace.</strong> It is claimed by 153
products and contradicted by 50, generating 134 separate reviews — more than any other archetype.
The pattern in the text is consistent: the product works, but the buyer needed a tutorial, a
developer, or three hours they were told they wouldn't need. Academy LMS is the cleanest case,
because its own FAQ asks <em>"Is Academy LMS easy to use?"</em> and answers <em>"Yes… you can get
started in minutes"</em> — and a 1★ reviewer with 28 helpful votes writes "I found the process
confusing and frustrating and decided to switch to another product." When the vendor answers the
question themselves, the contradiction is unambiguous.</p>

<p><strong>Support claims are the highest-stakes and least-audited.</strong> Only 19 products
explicitly promise responsive support, but 6 of them (32%) are contradicted — and those
contradictions are the most upvoted text in the entire negative corpus: DarkMySite's "Lifetime
priority support" against "I messaged support and no response" (20 helpful), ClickMoat's "24/7 Slack
support" against "I raised ticket, no response its been 4 days", SmatLeads' "24/7 priority live chat
support" against "NO response". Support promises are cheap to make at listing time and expensive to
keep for the life of a lifetime deal.</p>

<p><strong>The refund language is where a contradicted claim lands.</strong> The sharpest pairs are
not about broken features, they are about money: SendFox's "lifetime deal" against "my 'lifetime'
plan has a lifetime email sending limit and I must move onto a monthly subscription" (1★, 40
helpful); Forento's "free subdomain" against "holds your business hostage unless you upgrade… a
bait-and-upsell game" (3★, 47 helpful); The Link Chest's "unlimited" against "Anything useful in the
service requires an upgrade. This is the ultimate bait and switch" (1★, 32 helpful). In each case the
entry tier was genuinely as described and the <em>usable</em> product was not — which is why
"free/no hidden cost" is contradicted 11% of the time despite being one of the most concrete claims
a vendor can make.</p>

<p><strong>Concentration.</strong> 241 products have no detectable contradiction at all. Of the 101
that do, most have one. The tail is short and specific: BreezeDoc has seven distinct claims
contradicted at 62.8% satisfaction, TidyCal five at 80.7%, then SalesBlink, KingSumo and WP Reset Pro
with four each. Notably WP Reset Pro holds 98.6% satisfaction and ~1,312 reviews while still
accumulating four contradicted claims — high volume surfaces every edge case, so contradicted-claim
count should be read alongside review volume, not instead of it.</p>

<p><strong>Two caveats on these numbers.</strong> First, they are floors: a contradiction is only
detected when the reviewer happens to use language my pattern catches, so the true rates are higher.
Second, 27 reviews state the mismatch outright ("does not match the listing", "false advertising",
"bait and switch") without naming a claim archetype at all — those are counted separately and are
the highest-confidence evidence in the whole cross-reference.</p>
"""

import campaigns_section
CAMPAIGNS = campaigns_section.render()

html = (HTML.replace("__DATA__", blob)
            .replace('<div id="synth"></div>', "<div id=\"synth\">" + SYNTH + "</div>")
            .replace('<div id="synth2"></div>', "<div id=\"synth2\">" + SYNTH2 + "</div>")
            .replace('<div id="synth3"></div>', "<div id=\"synth3\">" + SYNTH3 + "</div>")
            .replace('<div id="synth4"></div>', "<div id=\"synth4\">" + SYNTH4 + "</div>")
            .replace('<div id="keyTakeaways"></div>', "<div id=\"keyTakeaways\">" + TAKEAWAYS + "</div>")
            .replace('<div id="soWhat"></div>', "<div id=\"soWhat\">" + SOWHAT + "</div>")
            .replace('<div id="confBox"></div>', "<div id=\"confBox\">" + CONFIDENCE + "</div>")
            .replace('<div id="campBody"></div>', "<div id=\"campBody\">" + CAMPAIGNS + "</div>"))
for tok in ("__DATA__", "__SYNTH"):
    assert tok not in html, f"unreplaced token {tok}"
for _id in ("synth", "synth2", "synth3", "synth4", "keyTakeaways", "soWhat", "confBox", "campBody"):
    assert f'<div id="{_id}"></div>' not in html, f"{_id} prose not injected"
assert html.count('<section id="campaigns"') == 1, "campaigns section missing"
assert 'data-t="campaigns"' in html, "campaigns nav tab missing"
assert len(CAMPAIGNS) > 20000, f"campaigns section suspiciously small: {len(CAMPAIGNS)}"

open(OUT, "w").write(html)

# Pages-ready standalone version: the artifact contract wants a body-only fragment, but
# GitHub Pages serves a real document. This HTML has zero external refs and no relative
# asset paths, so it works at any subpath with no base-tag or vite-style path config.
PAGES = os.path.join(HERE, "index.html")
open(PAGES, "w").write(
    "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
    "<title>AppSumo Catalog Intelligence — 342 products, promise vs delivery, campaign economics</title>\n"
    "<meta name=\"description\" content=\"Every live AppSumo product across all 27 browse "
    "categories: features, price ladders, derived sales volume, painpoints, claim-vs-complaint "
    "cross-reference, and campaign highlights — lifetime codes sold, gross revenue, velocity and "
    "contractual terms. Snapshot 2026-10-26.\">\n"
    "</head>\n<body>\n" + html + "\n</body>\n</html>\n")
open(os.path.join(HERE, ".nojekyll"), "w").write("")
print(f"wrote {PAGES} ({os.path.getsize(PAGES)/1e6:.2f} MB) + .nojekyll", file=sys.stderr)

print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.2f} MB)", file=sys.stderr)
