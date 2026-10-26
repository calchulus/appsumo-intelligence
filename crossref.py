"""Step 6: cross-reference each vendor's promise claims against its actual complaints.

Method: a claim archetype is a (promise pattern, contradiction pattern) pair. For each
product we find which archetypes its own listing copy asserts, then search that
product's negative reviews for the corresponding contradiction. Only claims the vendor
actually made are tested, so a complaint about "coding" only counts against a product
that promised "no coding".

Archetypes were derived from the real claim vocabulary (1,204 promise strings across
339 products) and from reading the negative corpus, not invented a priori.
"""
import json, os, re, collections, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (key, label, promise-side pattern, complaint-side contradiction pattern)
ARCHETYPES = [
    ("unlimited", "“Unlimited”",
     r"\bunlimited\b|\bno limits?\b|\bnever run out\b|\bas many as you (want|need)\b|\bno (restrictions?|caps?|throttl\w+)\b|\buncapped\b",
     # Must describe a limit being HIT or IMPOSED. The bare adjective "limited" is not a
     # contradiction: it produced false positives like "limited expectations" (Hedy AI) and
     # "limited to max 1MB per code file" against an "Unlimited traffic" claim (Editor.do),
     # which inflated this archetype to a bogus 38%.
     r"(ran out (of)?|run out of|hit (a|the|my) (limit|cap|quota|ceiling)|"
     r"reached? (the |my |a )?(limit|cap|quota)|"
     r"(limit|cap|quota|ceiling) (of|at|is|was) ?\d+|"
     r"limited to (\d+|a max(imum)? of \d+|only \d+)|"
     r"only (\d+|a few) (credits?|minutes?|words?|emails?|images?|uses?|seats?|tokens?|"
     r"domains?|projects?|reports?|sends?|websites?|users?)|"
     r"(usage|rate|sending?|send|monthly|daily|api) (limit|cap|quota)s?|"
     r"throttl\w+|not (really|truly|actually) unlimited|"
     r"unlimited[^.]{0,40}(a )?(lie|joke|false|misleading|not true|inaccurate|exaggerat\w+)|"
     r"(claims?|advertised|said|promised|listed)[^.]{0,30}unlimited[^.]{0,30}(but|however|yet))"),

    ("speed", "“In minutes / seconds / instant”",
     r"\bin minutes\b|\bin seconds\b|\binstant(ly)?\b|\bright away\b|\bimmediately\b|"
     r"\bno time\b|\bfast(est)?\b|\bquickly\b",
     r"\b(took (me |us )?(hours|days|weeks|forever|a long time|ages)|very slow|"
     r"so slow|takes (forever|a long time|ages|hours)|way too slow|not (fast|quick|"
     r"instant)|slow(er|est)? than|hours? to (get|set|complete|finish)|"
     r"waiting (for|on) (hours|days)|nothing (is |was )?instant)\b"),

    ("nocode", "“No code / no tech skills needed”",
     r"\bno[- ]?cod(e|ing)\b|\bwithout (any )?coding\b|\bno tech(nical)? (skills?|knowledge|"
     r"background|expertise)\b|\bnon[- ]technical\b|\bno programming\b|\bdoesn'?t require cod\w+",
     r"\b(requir(es?|ed) (coding|code|technical|developer|a developer|programming)|"
     r"need (to know|a developer|coding|technical)|you (have|need) to (code|know (html|css|code))|"
     r"not (really |truly )?no[- ]?code|developer (needed|required|help)|"
     r"had to (hire|get|ask) a (developer|programmer)|coding (skills?|knowledge) "
     r"(needed|required)|"
     # bare `html|css|javascript` matched incidental mentions; require that the reviewer
     # had to actually WRITE or KNOW it
     r"(need|needs|needed|require|requires|required|have to|had to|must|know|write|edit|"
     r"understand|touch|custom )[^.]{0,25}(html|css|javascript|custom code|code changes))\b"),

    ("ai_quality", "“AI-powered / AI does it”",
     r"\bAI[- ](powered|driven|generated|assisted)\b|\bwith AI\b|\busing AI\b|\bAI agents?\b|"
     r"\bAI (writes?|generates?|creates?|builds?|automates?)\b|\bGPT\b|\bLLM\b",
     r"\b(AI (is|was|were|output|results?|generation) (bad|poor|terrible|awful|useless|"
     r"inaccurate|generic|weak|disappointing|basic|horrible|not good|inconsistent)|"
     r"grammatical errors|hallucinat\w+|(output|results?|content|generation) (is|was|were) "
     r"(generic|inaccurate|poor|bad|useless|wrong|nonsense)|"
     r"(AI|model|generator) (doesn'?t|does not|didn'?t) (understand|work|produce)|"
     r"robotic|gibberish|worse than (chatgpt|writing it myself)|"
     r"better (results? )?(with|from|using) (chatgpt|claude|midjourney|adobe|free))\b"),

    ("allinone", "“All-in-one / replace N tools”",
     r"\ball[- ]in[- ]one\b|\breplace[sd]? \d+\+? tools\b|\bone (platform|place|tool|hub) "
     r"(for|to)\b|\beverything you need\b|\bcomplete solution\b|\bend[- ]to[- ]end\b",
     r"\b(missing (basic|key|essential|simple|obvious)? ?(features?|functionality)?|"
     r"lacks? (basic|key|essential|many)|not (an )?all[- ]in[- ]one|"
     r"still (need|use|had to use) (other|another|separate|multiple) (tools?|apps?|software)|"
     r"basic features? (are |is )?(missing|absent)|doesn'?t (replace|do everything)|"
     r"had to (go back|return) to|not a (complete|full) (solution|replacement))\b"),

    ("dragdrop", "“Drag-and-drop / visual builder”",
     r"\bdrag[- ]and[- ]drop\b|\bvisual (builder|editor)\b|\bno[- ]code (builder|editor)\b",
     r"\b(no drag[- ]and[- ]drop|not drag[- ]and[- ]drop|drag[- ]and[- ]drop (doesn'?t|does not|"
     r"isn'?t|is (broken|missing|not))|missing.{0,20}drag|hard to (edit|customize|build)|"
     r"no (visual |way to )?(builder|editor)|editor (is|was) (broken|limited|missing))\b"),

    ("whitelabel", "“White-label / your branding”",
     r"\bwhite[- ]?label\b|\byour (own )?brand(ing|ed)?\b|\bunbranded\b|\brebrand\w*|"
     r"\bwithout .{0,20}branding\b|\bcustom branding\b|\byour logo\b",
     r"\b(branding (still|is still|shows|remains|appears)|not (really |truly |fully )?"
     r"white[- ]?label|white[- ]?label (doesn'?t|does not|isn'?t|is (not|limited|broken))|"
     r"(their|the|vendor|company) (logo|branding|brand) (still )?(shows?|appears?|visible)|"
     r"can'?t (remove|replace) (the )?(logo|branding)|powered by .{0,24}(visible|shows))\b"),

    ("support247", "“24/7 or responsive support”",
     # The 24/7 or live-chat claim must be attached to SUPPORT. "24/7 agents" (FuseBase) and
     # "photos removed within 24 hours" (ImageColorizer) are product claims, not service
     # promises; matching them against support complaints is a category error.
     r"(24/7|24 hours a day|round[- ]the[- ]clock|24x7)[^.]{0,45}(support|service|help|chat|assistance)|"
     r"(support|service|help|assistance)[^.]{0,45}(24/7|24 hours|round[- ]the[- ]clock)|"
     r"\blive (chat|support)\b|\bresponsive (support|team)\b|"
     r"\bdedicated (support|account manager|success manager)\b|\bpriority support\b|"
     r"\bsupport (within|in) \d+ ?(hours?|minutes?|days?)\b|"
     r"\b(first[- ]class|excellent|great|fast) (customer )?(service|support)\b",
     r"\b(no (response|reply|support)|never (responded|replied|answered)|"
     r"support (is|was) (non[- ]?existent|useless|unresponsive|terrible|awful|slow|bad)|"
     r"ignored|waiting (for|on) (a )?(reply|response|support)|unanswered|"
     r"no (live )?(chat|support)|doesn'?t respond|ticket.{0,20}(no|never))\b"),

    ("lifetime", "“Lifetime / forever access”",
     r"\blifetime\b|\bforever\b|\bfor life\b|\bone[- ]time (payment|purchase|fee|price)\b",
     # `expired` needs licence/access context. Bare "expired" produced 5 false positives in
     # an 8-review sample: a cookie error ("this page has expired"), an OAuth session lapse,
     # the reviewer's PREVIOUS VPN subscription ending, and marketing email subject lines.
     r"\b(lifetime (is|was) (a )?(lie|joke|not|false)|not (really|truly|actually) lifetime|"
     r"lost access (to|entirely)?|"
     r"no longer have access to (the |my |anything|everything|all|any of)|"
     r"access (was|is|has been|got) (revoked|removed|lost|gone|taken away|stripped)|"
     r"(my|the|our) (license|licence|account) (was|has been|got) "
     r"(suspended|revoked|terminated|deleted|banned|removed|locked)|"
     r"(my|the) (lifetime|lifetime plan|deal) (has |have |was )?(expired?|lapsed|ended|revoked)|"
     r"now (requires|charges|asks|needs) (a )?(monthly|subscription)|"
     r"forced (to|into) (a )?(subscription|monthly)|"
     r"(product|company|service|platform|roadmap) (is|was|has been) "
     r"(discontinued|shut ?down|sunset|dead|abandoned|no longer active)|"
     r"shut ?(down|off) (the|their)? ?(product|service|platform|company|site)|"
     r"went out of business|additional (monthly )?(fee|cost|charge)s? (to keep|for continued))\b"),

    ("ease", "“Easy / simple / effortless / seamless”",
     r"\beasy\b|\bsimple\b|\beffortless\b|\bseamless\b|\buser[- ]friendly\b|\bintuitive\b|"
     r"\bbeginner[- ]friendly\b|\bplug and play\b|\bturnkey\b|\bhands[- ]off\b",
     r"\b(not (easy|simple|intuitive|user[- ]friendly)|hard to (use|set ?up|understand|navigate)|"
     r"difficult to (use|set ?up|understand|navigate)|confus(ing|ed)|steep learning curve|"
     r"complicated|clunky|frustrating|overwhelming|poor (ui|ux|interface)|"
     r"unintuitive|far from (easy|simple|seamless)|not seamless|anything but (easy|simple))\b"),

    ("automate", "“Automate / no manual work”",
     r"\bautomat(e|es|ed|ion|ic)\w*\b|\bno manual\b|\bwithout manual\b|\bautopilot\b|"
     r"\bset (it )?and forget\b|\bauto[- ]?\w+\b",
     r"\b(manual(ly)? (again|work|process|steps?)|still (manual|have to do it manually)|"
     r"not (automated|automatic)|doesn'?t (automate|work automatically)|"
     r"had to (do it )?manual|automation (doesn'?t|does not|failed|broke|is broken)|"
     r"no automation|more (manual )?work than)\b"),

    ("integrations", "“N+ integrations / connectors”",
     r"\b\d+\+? (integrations?|connectors?|apps?|platforms?|tools?|templates?|models?)\b|"
     r"\bintegrates? with\b|\bintegrations?\b",
     r"\b(integration (doesn'?t|does not|failed|is broken|doesn'?t work|not working)|"
     r"integrations? (are|were) (broken|outdated|limited|missing)|"
     r"doesn'?t (integrate|sync|connect) (with)?|cannot (integrate|connect|sync)|"
     r"(no|lacks?) .{0,20}integration|api (doesn'?t|does not) (work|exist)|"
     r"failed to (sync|connect|import|export)|not (compatible|integrating) with)\b"),

    ("free_claim", "“Free / no hidden cost”",
     r"\bfree\b|\bno hidden (cost|fee)s?\b|\bno extra cost\b|\b\$0\b",
     r"\b(upsell\w*|hidden (cost|fee|charge)s?|extra (cost|fee|charge)s?|"
     r"pay (more|extra|again)|not (really |actually |truly )?free|"
     r"requires? (a |another )?(paid|premium|subscription)|additional (cost|fee|charge)s?|"
     r"bait|only the free|free (tier|version) (is|was) (useless|limited|nothing))\b"),

    ("proven", "“Proven / guaranteed results”",
     r"\bproven\b|\bguarantee[ds]?\b|\bresults? guaranteed\b|\btested (and )?proven\b|"
     r"\b\d+% (accuracy|success|increase|boost)\b",
     # `didn'?t work` was removed: a plain bug report is not a contradiction of a
     # "proven results" claim, and it made 3 of 4 sampled matches false positives.
     r"\b((no|zero|little) (real )?results?|"
     r"(results?|accuracy|numbers?) (were|was|are) (bad|poor|inaccurate|nowhere|misleading|wrong|fake)|"
     r"false (advertising|claims?|promises?)|"
     r"(listing|description|sales page|claim|advertisement|ad) (is|was) (misleading|inaccurate|"
     r"false|wrong|exaggerated)|"
     r"doesn'?t (live|deliver) up to (the |its |their )?(claims?|promise|hype|advert)|"
     r"overpromis\w+|exaggerat\w+|misleading|"
     r"nowhere near (the )?(claimed|promised|advertised|\d+))\b"),

    ("explicit_mismatch", "Buyer states listing ≠ product (any claim)",
     None,  # matched directly in review text, no promise precondition
     r"\b(does ?n[o']?t match (the |what was |their )?(listing|description|advertised|sales page|"
     r"appsumo|terms|page)|not (what|as) (was )?(advertised|described|promised|listed)|"
     r"false advertising|misleading (listing|description|advert|offer|title)|"
     r"bait[- ]and[- ]switch|deceptive|"
     r"(listing|description|sales page|ad) (is|was) (misleading|inaccurate|false|wrong)|"
     r"delivered does not match|doesn'?t do what (it|they) (says|claims|advertise)|"
     r"not as described|rip[- ]?off)\b"),
]

COMPILED = [(k, lab, re.compile(pp, re.I) if pp else None, re.compile(cp, re.I))
            for k, lab, pp, cp in ARCHETYPES]


def boilerplate_terms(products, min_products=25):
    """plan_terms mixes real vendor claims ("Lifetime access to KingSumo") with AppSumo's
    contractual boilerplate. Any term string repeated across >25 products is by definition
    not a product-specific claim, so it must not be treated as a promise. Measured offenders:
    "redeem your code(s) within 60 days" (164x), "This deal is not stackable" (68x),
    "created by the AppSumo team as a simple, affordable solution" (34x) -- the last one was
    fabricating an "Easy/simple" claim for products that never made it.
    """
    c = collections.Counter()
    for p in products:
        for t in (p.get("plan_terms") or []):
            c[re.sub(r"\s+", " ", t).strip().lower()] += 1
    bad = {t for t, n in c.items() if n >= min_products}
    # Marketplace-authored copy is not a vendor claim regardless of frequency.
    # "An AppSumo Original, created by the AppSumo team as a simple, affordable solution"
    # appears in only 6 products (under the threshold) but was fabricating an "Easy/simple"
    # claim for SendFox and Million Dollar Email Templates.
    bad |= {t for t in c if t.startswith("an appsumo original")
            or "created by the appsumo team" in t or t.startswith("appsumo original")}
    return bad


# VERIFIED FAQ contamination -- one product, excluded by slug on evidence, not heuristic.
# AppSumo's `faqs` for `switchy` (deal_id 1900) belong to a DIFFERENT product: a Bangalore
# smart light-switch retrofit. Its listing says "Boost conversions with retargeting links",
# alternative_to = Bitly/Linktree/Rebrandly, yet the FAQs ask "How do I install Switchy?
# ... about 5 minutes for a trained electrician. Free installation is available in Bangalore
# City", "Can I operate my existing switch after installing Switchy?", "Is WiFi mandatory?".
# This fabricated a "Free" claim that then matched a genuine complaint ("Pay more to
# literally anyone else", 37 helpful votes) -- a false contradiction.
#
# A vocabulary-overlap detector was tried and REJECTED: Switchy scores 6.29% FAQ-to-listing
# word overlap, above the 5th percentile (2.2%, median 9.2%) across all 194 products with
# FAQs. Generic software words (app, install, device, manage, control) mask the mismatch, so
# any threshold low enough to catch Switchy also flagged 9 legitimate products. Ship the one
# verified exclusion rather than a heuristic that misses its motivating case.
FAQ_EXCLUDE = {"switchy"}

BOILER = set()


def promise_text(p, full=None):
    """Union of BOTH promise sources. Neither alone is sufficient:
      - analysis.json carries the structured claims (core_features like "Unlimited chat",
        feature x tier matrix entries, plan terms)
      - promise.jsonl carries the listing copy (html_body, tldr, feature blocks) and the
        vendor's own FAQs, which is where white-label / 24-7 / "as many as you want" live
    Measured: whitelabel 39->61, speed 55->107, easy 68->125 from the copy, but
    unlimited 113->54 (it lives in the feature lists). Union captures both.
    """
    pr = p["promise"]
    parts = [pr.get("value_prop") or "", pr.get("subheader") or "",
             *(pr.get("highlights") or []), p.get("tagline") or "",
             *(f"{f.get('feature')} {f.get('tooltip') or ''}" for f in (p.get("core_features") or [])),
             *(p.get("common_features") or []),
             *(t for t in (p.get("plan_terms") or [])
               if re.sub(r"\s+", " ", t).strip().lower() not in BOILER),
             *(f.get("feature") or "" for f in (p.get("feature_matrix") or []))]
    for f in (p.get("feature_matrix") or []):
        parts += [str(v) for v in (f.get("by_tier") or {}).values()]
    if full:
        parts += [full.get("value_prop") or "", full.get("subheader") or "",
                  full.get("tldr") or "", full.get("meta_title") or "",
                  *(full.get("highlights") or []), full.get("body") or "",
                  full.get("overview") or ""]
        for fb in (full.get("feature_blocks") or []):
            parts.append(fb.get("title") or "")
            parts += fb.get("bullets") or []
        for fq in (full.get("faqs") or []):
            if p.get("slug") in FAQ_EXCLUDE:
                continue          # verified wrong-product FAQ - see FAQ_EXCLUDE note
            parts.append(f"{fq.get('q') or ''} {fq.get('a') or ''}")
    return re.sub(r"\s+", " ", " ".join(t for t in parts if t)).strip()


def excerpt(t, start, width=160):
    a, b = max(0, start - width), min(len(t), start + width)
    return ("…" if a > 0 else "") + re.sub(r"\s+", " ", t[a:b]).strip() + ("…" if b < len(t) else "")


def main():
    global BOILER
    A = json.load(open(os.path.join(HERE, "analysis.json")))
    BOILER = boilerplate_terms(A["products"])
    print(f"filtered {len(BOILER)} boilerplate plan_terms strings out of claim detection",
          file=sys.stderr)
    full_promise = {}
    pp = os.path.join(HERE, "promise.jsonl")
    if os.path.exists(pp):
        for line in open(pp):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    full_promise[r["slug"]] = r
                except Exception:
                    pass
    print(f"loaded full promise text for {len(full_promise)} products", file=sys.stderr)

    negs = collections.defaultdict(list)   # deal_id -> [(star, text, up)]
    for line in open(os.path.join(HERE, "reviews.jsonl")):
        r = json.loads(line)
        for k, b in (r.get("buckets") or {}).items():
            for c in (b.get("comments") or []):
                t = (c.get("comment") or "").strip()
                if t:
                    negs[r["deal_id"]].append((int(k), re.sub(r"\s+", " ", t),
                                               c.get("up_votes") or 0))

    rows, arch_stats = [], collections.defaultdict(lambda: {"claims": 0, "contradicted": 0,
                                                            "reviews": 0})
    plen = []
    for p in A["products"]:
        pt = promise_text(p, full_promise.get(p["slug"]))
        plen.append(len(pt))
        revs = negs.get(p["deal_id"], [])
        hits = []
        for key, label, prx, crx in COMPILED:
            promised = None
            if prx is not None:
                m = prx.search(pt)
                if not m:
                    continue
                promised = excerpt(pt, m.start(), 70)
            arch_stats[key]["claims"] += 1 if prx is not None else 0
            found = []
            for star, t, up in revs:
                m = crx.search(t)
                if m:
                    found.append({"star": star, "up": up, "matched": m.group(0).lower(),
                                  "ctx": excerpt(t, m.start())})
            if not found:
                continue
            found.sort(key=lambda f: (-f["up"], -len(f["ctx"])))
            if prx is not None:
                arch_stats[key]["contradicted"] += 1
            arch_stats[key]["reviews"] += len(found)
            hits.append({"claim": key, "label": label, "promised": promised,
                         "n_reviews": len(found), "examples": found[:4]})
        if hits:
            hits.sort(key=lambda h: -h["n_reviews"])
            rows.append({"deal_id": p["deal_id"], "name": p["name"], "slug": p["slug"],
                         "url": p["url"], "category": p["category"], "group": p["group"],
                         "promise": p["promise"], "neg_reviews": len(revs),
                         "satisfaction": p["fulfillment"]["satisfaction_rate"],
                         "rating": p["rating"], "review_count": p["review_count"],
                         "sold_estimate": p["sold_estimate"], "sales_method": p["sales_method"],
                         "entry_price": p["entry_price"],
                         "n_contradicted_claims": len(hits), "contradictions": hits})

    rows.sort(key=lambda r: (-r["n_contradicted_claims"], -r["neg_reviews"]))

    plen.sort()
    out = {
        "products_analyzed": len(A["products"]),
        "products_with_claims": sum(1 for x in plen if x >= 100),
        "promise_text_median_chars": plen[len(plen) // 2],
        "promise_text_total_chars": sum(plen),
        "products_with_contradiction": len(rows),
        "boilerplate_terms_filtered": len(BOILER),
        "faq_excluded_verified": sorted(FAQ_EXCLUDE),
        "total_contradiction_reviews": sum(h["n_reviews"] for r in rows for h in r["contradictions"]),
        "archetype_labels": {k: lab for k, lab, _, _ in ARCHETYPES},
        "archetype_stats": {
            k: {**v, "contradiction_rate": round(v["contradicted"] * 100 / v["claims"], 1)
                if v["claims"] else None}
            for k, v in arch_stats.items()},
        "rows": rows,
    }
    json.dump(out, open(os.path.join(HERE, "promise_crossref.json"), "w"),
              indent=1, ensure_ascii=False)

    print(f"products analysed: {out['products_analyzed']} (with promise text: {out['products_with_claims']})",
          file=sys.stderr)
    print(f"products with >=1 contradicted claim: {out['products_with_contradiction']}", file=sys.stderr)
    print(f"contradicting reviews found: {out['total_contradiction_reviews']}", file=sys.stderr)

    print("\n%-34s %7s %11s %9s %8s" % ("CLAIM ARCHETYPE", "CLAIMED", "CONTRADICTED", "RATE", "REVIEWS"),
          file=sys.stderr)
    st = out["archetype_stats"]
    for k, v in sorted(st.items(), key=lambda x: -(x[1]["contradiction_rate"] or 0)):
        lab = out["archetype_labels"][k]
        rate = f"{v['contradiction_rate']:.0f}%" if v["contradiction_rate"] is not None else "n/a"
        print("%-34s %7d %11d %9s %8d" % (lab[:34], v["claims"], v["contradicted"], rate,
                                          v["reviews"]), file=sys.stderr)

    print("\n=== TOP 18 PRODUCTS BY CONTRADICTED CLAIMS ===", file=sys.stderr)
    for r in rows[:18]:
        cl = ", ".join(f"{h['label'].strip(chr(8220)+chr(8221))}×{h['n_reviews']}"
                       for h in r["contradictions"][:4])
        print(f"  {r['n_contradicted_claims']} claims | sat {r['satisfaction']}% | neg {r['neg_reviews']:>3} | "
              f"{r['name'][:28]:<29} {cl}", file=sys.stderr)


if __name__ == "__main__":
    main()
