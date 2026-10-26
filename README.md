# AppSumo Catalog Intelligence

Every live AppSumo product across all 27 browse categories, with per-product feature maps,
price ladders, **derived sales volume**, painpoints mined from real customer reviews, and a
cross-reference of each vendor's claims against what their own buyers complained about.

**Snapshot: 2026-10-26.** 342 products · 24,797 reviews (8,208 read verbatim) · 5,841
pre-purchase questions · 75 promotional campaigns (2021–2026) · 622,571 license codes issued
(497,195 paid + 541,733 freebie downloads) · **$30.38M gross marketplace revenue**.

**Live dashboard:** https://calchulus.github.io/appsumo-intelligence/

---

## Headline findings

**The softest claims fail hardest; the hardest ones hold.** "Easy / simple / seamless" is
contradicted by customers in **33%** of the products that claim it, and "all-in-one / replace N
tools" in **29%**. "Lifetime access" — the boldest promise on the marketplace — is contradicted in
only **2%**. Vague adjectives are unfalsifiable at purchase and disappointing in use; checkable
claims mostly get delivered.

| Claim archetype | Products claiming | Contradicted | Rate |
|---|---|---|---|
| Easy / simple / effortless / seamless | 153 | 50 | **33%** |
| 24/7 or responsive support | 19 | 6 | **32%** |
| All-in-one / replace N tools | 49 | 14 | **29%** |
| Unlimited | 174 | 25 | 14% |
| Proven / guaranteed results | 29 | 4 | 14% |
| Free / no hidden cost | 121 | 13 | 11% |
| In minutes / seconds / instant | 160 | 15 | 9% |
| AI-powered | 123 | 10 | 8% |
| No code / no tech skills | 47 | 3 | 6% |
| N+ integrations | 148 | 9 | 6% |
| Automate / no manual work | 184 | 4 | 2% |
| Lifetime / forever access | 312 | 6 | 2% |
| White-label | 90 | 1 | 1% |

**101 of 342 products** have at least one claim contradicted by their own negative reviews, plus
**27 reviews** where the buyer states outright that the listing did not match the product.

**Complaints are delivery failures, not feature requests.** Across 2,389 negative reviews (86% of
all 1–3★ reviews on the site): missing feature / promise gap 19.6%, broken 18.5%, refund sought
17.5%, limits too tight 17.2%, integration 13.2%, setup/docs 12.3%, poor UI 8.3%, unreliable 7.7%,
support unresponsive 6.9%, poor value 4.1%, deal devalued 3.2%, AI output quality 2.4%, access lost
0.5%. Support is the hinge — the recurring sequence in the text is *product broke → support silent →
refund*.

**High satisfaction, thin corroboration.** Median satisfaction is **89.8%** (4–5★ share, from
AppSumo's complete star counts), but only **6.3%** of positive reviews actually say the product did
the job it was sold to do, versus **23.3%** praising how easy it was. Only **165 of 250** judgeable
products have even one buyer explicitly confirming the outcome. **5.7%** of positive reviews are
anticipatory — written before real use. A five-star rating here is weaker evidence than it looks.

**Willingness to pay is a stacking game, not a value estimate.** Median top-tier is **5×** entry,
max **61×** (ResumeUp.AI, $49 → $2,999). But 94 products run a *linear* ladder (flat price per
added code), meaning the marginal buyer is an agency stacking identical licences — a distribution
channel, not a pricing strategy. Only 89 progressive ladders genuinely segment by buyer size; 159
products have too few priced tiers to classify. And
ceiling ≠ revenue: LeadOcean lists a $1,999 top tier against 1 derived unit sold.

**Volume is brutally concentrated.** 497,195 paid license codes across 168 listings, median
**1,372** per product. The top 5 listings are **31%** of measured gross revenue and the top 20 are
**59%**, leaving 41% in a long tail of ~148 listings. Revenue leaders: WordHero (~34,875 units @ $89 ≈ $3.1M),
Reoon Email Verifier (~26,197 @ $79 ≈ $2.1M), Switchy (~43,142 @ $39). The single largest number on
the site — 66,456 — is a *free* lead magnet, which is why paid units and free downloads are ranked
separately throughout.

**What wins is unglamorous and narrow.** Link-in-bio, AI content writing, email verification,
spreadsheet templates, business courses — recurring manual chores removed for under $90. The AI
products that sold are AI *applied to an existing chore*, not AI as the product. The best-evidenced
performers make narrow, one-session-verifiable promises: Reoon ("protect your email server's
reputation", 98.5% satisfaction, 756 reviews), Switchy ("boost conversions with retargeting links",
96.7%).

**Deal devaluation is AppSumo's own structural risk.** 3.2% of negative reviews complain the current
offer is worse than an earlier one for the same product ("stripped things down and still charge
more"). Small share, distinctive target: the anger is at the *marketplace's* repricing, not the
vendor's product, and it lands on repeat buyers.

---

## Units sold: derived, and validated

AppSumo publishes no `units_sold` or revenue field anywhere. But it does publish
`active_codes` and `codes_remaining`, and:

```
license_codes_sold ≈ active_codes − codes_remaining
```

This counts **license codes, not purchases** — 93 of the 168 paid listings sell tiers granting more
than one code per purchase (up to 10), so one order can mint several codes. Revenue is computed per
code from each tier's price-per-code, giving a floor–ceiling range that collapses to an exact figure
for the 91 listings whose ladder is linear in price-per-code. It is **gross marketplace take, not
vendor net**: AppSumo's split is not published per deal, so nothing here is profit.

This is **testable**, because free products publish a true `freebie_downloads_total`. Across the 6
freebies having all three fields the formula matches at **0.3% median error**, worst 1.7% (The Sauce:
implied 4,986 vs actual 4,985).

Two limits, both reflected in the dashboard:

- **Coverage is 174 of 342.** The other 133 have `uses_codes: false`, so `review_count` is their only
  proxy. They are ranked in a separate band and never blended with derived units.
- **Revenue is a floor.** `units × entry-tier price` ignores buyers who stacked to higher tiers, and
  does not deduct AppSumo's cut.

---

## Data & pipeline

Nine passes over AppSumo's own JSON APIs. Nothing was scraped by rendering — every number comes
from the JSON the site serves itself.

| # | Source | Records | What it gave |
|---|---|---|---|
| 1 | `/api/v2/deals/esbrowse/` × 27 categories | 342 | catalog, price, rating, taxonomy, `active_codes` |
| 2 | `/api/v2/deals/<id>/` × 342 | 342/342 | feature×tier matrix, star breakdown, plan terms |
| 3 | `/products/<slug>/` `__NEXT_DATA__` × 342 | 342/342 | full tier ladders (1,057 plan rows = 1,048 sellable tiers + 9 Plus tiers) — absent from the API |
| 4 | `/api/v2/deals/<id>/reviews/?rating=N` | 7,405 | verbatim 1–3★ text |
| 5 | `/api/v2/deals/<id>/reviews/?rating=4,5` | 5,819 | verbatim 4–5★ text (sampled) |
| 6 | `/api/v2/deals/<id>/questions/` | 5,841 | pre-purchase questions |
| 7 | esbrowse `story_details` / `story_highlights` | 342 | vendor's stated promise |
| 8 | `story.html_body`, `faqs`, `overview_media` | 342/342 | full listing copy — 0.5M chars of body text + 1,672 FAQs |
| 9 | `crossref.py`, 13 claim archetypes | 101 | promise → complaint pairs |
| 10 | `campaigns.py` — `plans[].codes`, plan terms, dates | 203 | campaign economics: gross revenue, $/day velocity, refund & redemption windows |
| 11 | `campaign_history.py` — `participation` field | 75 campaigns | promotional calendar, tenure-controlled promotion analysis |

### Reproduce

```bash
python3 crawl_all.py          # 27 categories -> appsumo_all_products.{csv,json}, categories/
python3 crawl_details.py      # -> details.jsonl
python3 crawl_pages.py        # -> pages.jsonl   (tier ladders)
python3 crawl_reviews.py      # -> reviews.jsonl (1-3 star)
python3 crawl_positive.py     # -> positive.jsonl (4-5 star)
python3 crawl_promise.py      # -> promise.jsonl  (full listing copy + FAQs)
python3 analyze.py            # -> analysis.json
python3 crossref.py           # -> promise_crossref.json
python3 campaigns.py          # -> campaign_highlights.json    (economics)
python3 campaign_history.py   # -> campaign_participation.json (promo calendar)
python3 build_dashboard.py    # -> index.html + appsumo_dashboard.html
python3 test_dashboard.py     # 104 headless render assertions
```

Every crawler is resumable (skips ids/slugs already on disk) and checkpoints per record. Only
`curl` and the Python stdlib are required; `test_dashboard.py` needs `browser-use`.

### Repo layout

```
index.html                     GitHub Pages build (standalone document, 7 tabs)
appsumo_dashboard.html         same, as a body-only artifact fragment
appsumo_all_products.csv/json  master product list (342)
appsumo_categories_summary.csv per-category counts
categories/                    54 files, one CSV+JSON per category
analysis.json                  merged per-product analysis dataset
promise_crossref.json          claim -> complaint pairs with verbatim evidence
campaign_highlights.json       campaign economics (revenue, velocity, contract terms)
campaign_participation.json    promotional calendar + tenure-controlled analysis
details|pages|reviews|positive|promise.jsonl   raw crawl layers
crawl_*.py analyze.py crossref.py campaigns.py campaign_history.py
build_dashboard.py test_dashboard.py
summary_text.py                dashboard prose (takeaways / guidance / confidence / lessons)
campaigns_section.py           renders the campaign-economics section server-side
strip_pii.py                   reviewer-identity scrubber (see Privacy)
```

---

## Method notes worth stealing

**The category pages are Next.js SSG and only server-render page 1.** `?page=2` is ignored and
there is no pagination markup in the HTML, so the API is the only route to the rest. Pagination is
cursor-based (`search_after`).

**Finding a private API:** download the `_next/static/chunks/*.js` listed in the HTML and regex for
`/api/...`. 19 chunks → 58 endpoints in one parallel sweep. Then grep the chunk for the endpoint
name to get the *query-builder source*, which yields the exact param whitelist and mapping. Here:
URL path slugs map to `attribute[<slug>]` params, so
`/operations/productivity-automation/` → `attribute[group]=operations&attribute[category]=productivity-automation`.
Percent-encode the bracket keys; a naive `tags=a,b` silently returns a wrong, much smaller result
set (2 vs 33) rather than an error.

**`per_page` is honoured up to at least 250** on esbrowse, so each category is one request.

**The reviews endpoint hard-caps at 20 records** and ignores `page`, `per_page`, `offset`, `limit`,
`count`, `size`, `search_after` and every `sort` value — **but it honours `rating=N`**. Negatives are
only 11% of the corpus and just 17 products have a bucket above 20, so iterating `rating=1,2,3`
yields near-complete negative coverage (86%). `rating=4,5` gives a 26% sample of positives.

**Verification that replaced a browser check.** (1) API page-1 slug set must equal the
`__NEXT_DATA__` page-1 slug set exactly; (2) fetched count equals `meta.total_results`; (3) de-dupe
by `id`; (4) **assert every returned item's own embedded `taxonomy` matches the category it was
fetched under** — the strongest check, it catches wrong-category leakage that count-matching misses;
(5) reconcile per-subcategory counts against the page's own facet `doc_count`s. All five agreed, so
page 2 was proven without ever rendering it.

**Tagging was audited, not assumed.** Four regex bugs were found by reading matched substrings in
context, each of which would have silently corrupted the results:

1. `re.X` (verbose) strips unescaped whitespace, so `no response` compiled to `noresponse` —
   support and value themes undercounted ~5×.
2. `import\w*` matched "**important**", inflating the integration theme to #1 (495 → 316 after fix).
3. Bare `limited` matched "limited expectations" and "limited to 1MB per code file" against an
   "Unlimited *traffic*" claim — inflating the unlimited contradiction rate from a true 14% to a
   bogus 38%.
4. Bare `expired` matched a cookie error, an OAuth session lapse, and a reviewer's *previous* VPN
   ending (5 of 8 sampled were false).

**All theme counts are mentions, not complaints.** A review can trip several themes, and a keyword
can land in a positive clause inside an otherwise-negative review. Every quote in the dashboard
shows the exact trigger token and a match-centred excerpt so each call can be judged. Contradiction
rates are **floors** — a contradiction is only detected when the reviewer happens to use language
the pattern catches.

---

## Privacy

Reviewer identity is **not** published. `strip_pii.py` removed the `user_name` field (AppSumo
returns `full_name`, `username` or `email` depending on account) from all 19,065 comment records,
and redacted **2,044 email addresses** found in review free-text — vendor contacts and reviewer
work addresses, which are more identifying than the usernames. The crawlers no longer capture
identity at all, so re-runs stay clean.

What remains is review text, star rating and helpful-vote count. Free text may still contain names
or businesses that reviewers chose to write; that cannot be scrubbed mechanically without damaging
the quotes. All of it was publicly visible on AppSumo's product pages at collection time.

---

## Source-data problems found

- **AppSumo's FAQs for `switchy` belong to a different product.** Switchy is a Bitly/Linktree
  competitor ("Boost conversions with retargeting links"), but its listing FAQs ask *"How do I
  install Switchy? … about 5 minutes for a trained electrician. Free installation is available in
  Bangalore City"*, *"Can I operate my existing switch after installing Switchy?"*, *"Is WiFi
  mandatory?"* — a smart light-switch retrofit. This fabricated a "Free" claim that then matched a
  genuine complaint, so those FAQs are excluded by slug. A vocabulary-overlap detector was built to
  find such cases automatically and **rejected**: Switchy scores 6.29% FAQ-to-listing word overlap
  against p5 = 2.2% / median 9.2%, so no threshold catches it without also flagging nine legitimate
  products.
- **`plan_terms` mixes vendor claims with AppSumo's contractual boilerplate.** "You must redeem your
  code(s) within 60 days" appears in 164 products; "An AppSumo Original, created by the AppSumo team
  as a *simple, affordable* solution" (only 6 products, so a frequency filter misses it) was
  fabricating an "easy/simple" claim. 14 such strings are filtered.
- **`/api/v2/deals/?slug=X` silently ignores the slug** and returns an arbitrary deal — it returned
  `vectera-2019` (expired) when asked for `betterclaw`. Both crawlers assert returned slug ==
  requested slug; 0 mismatches across 684 fetches.
- **`would_recommend` is collected but never populated** — 0 across all 342 products and every
  review, so it could not be used as a satisfaction signal.
- **Plus-exclusive variants are separate listings sharing the parent's reviews.** Screpy and
  Screpy-Plus return byte-identical review sets (914 reviews each). Any "best-reviewed" ranking
  double-counts them; collapse by name prefix, not by id.

---

## Caveats

1. Units sold are derived, not published. Validated at 0.3% median error on freebies — the only
   place it could be checked. Treat paid-product figures as estimates.
2. Revenue is a floor (entry-tier price, no AppSumo cut deducted).
3. `sold_estimate` counts **license codes, not purchases**; revenue is gross marketplace take,
   not vendor net (AppSumo's split is unpublished).
4. Positive review **text** is a 26% sample; satisfaction **rates** are exact for all 342.
5. Questions are the 20 most recent per product (5,841 of 21,832 on site) — skews recent.
6. Contradiction rates are floors, and count "contradicted at least once", not "share of buyers who
   noticed".
7. Residual known weakness: for chat-widget vendors (AnyChat, Support Board) "live chat" is the
   product rather than their support, so 2 of 6 support-claim contradictions are semantic mismatches.
8. Snapshot, not a time series. Prices, stock and codes move constantly.

---

Collected 2026-10-26 from public AppSumo endpoints. Product names, prices and review text belong to
their respective vendors and reviewers; this is research analysis, not an AppSumo-affiliated project.
