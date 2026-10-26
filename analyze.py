"""Step 4: merge all layers into one analysis dataset.

Layers: appsumo_all_products.json (browse) + details.jsonl (per-product API)
      + pages.jsonl (tier ladders) + reviews.jsonl (review/question text)

Produces analysis.json: per-product features, willingness-to-pay curve,
derived sales volume, and mechanically-tagged painpoint themes.
"""
import json, os, re, collections, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- theme taxonomy
# Built by reading ~1,650 real 1-3 star reviews + ~4,000 pre-purchase questions,
# not guessed. Order matters: first match wins for the "primary theme" label,
# but every product records all themes it hits.
PAIN_THEMES = [
    ("deal_devalued", "Deal devalued vs earlier offer",
     r"\b(old deal|previous deal|new deal|last year'?s deal|used to (be|include|have)|"
     r"rip[- ]?off|stripped|cut (out|back)|removed features?|downgrad\w+|worse than (before|the old)|"
     r"bait|deceptive|misleading (deal|offer)|not what (i|we) (bought|purchased)|changed the deal|"
     r"less (features|value)|more expensive (now|than))\b"),
    ("access_lost", "Access lost / product sunset",
     r"\b(lost access|no longer (available|works|exists)|shut ?down|discontinued|sunset|"
     r"account (was )?(suspended|deleted|locked)|stopped working entirely|went out of business|"
     r"company (disappeared|gone)|cannot (log ?in|access) anymore|grinding halt)\b"),
    ("support_unresponsive", "Support unresponsive",
     r"\b(no response|never (responded|replied|answered)|support (is|was) (non[- ]?existent|useless|"
     r"unresponsive|terrible|awful|slow)|ignored|waiting (for|on) (a )?(reply|response|support|"
     r"refund)|ticket.{0,20}(no|never)|unanswered|doesn'?t respond|zero support|no support|"
     r"lack of (customer )?(service|support|responsiveness)|no customer (service|support)|"
     r"customer (service|support) (is|was) (bad|poor|terrible|non[- ]?existent|awful|slow|lacking))\b"),
    ("broken", "Broken / does not work",
     r"\b(does ?n[o']?t work|doesn'?t work|not working|broken|error 500|500 error|server error|"
     r"crash\w*|bug(s|gy)?|failed to (load|save|send|export|import)|won'?t load|not loading|"
     r"keeps failing|malfunction|unusable|completely broken|stopped working)\b"),
    ("refund_friction", "Refund sought / refund friction",
     r"\b(refund\w*|money back|not refunded|denied my|charge ?back|reimburse)\b"),
    ("ai_quality", "AI output quality poor",
     r"\b(grammatical errors|hallucinat\w*|inaccurate|generic (output|content|results)|"
     r"(ai|model|output|generation|results?) (is|are|was|were) (basic|poor|bad|weak|terrible|"
     r"awful|useless|inaccurate|disappointing)|robotic|nonsense|gibberish|not accurate|"
     r"poor quality|low quality|amateur)\b"),
    ("limits_credits", "Limits / credits too tight",
     r"\b(credits?|tokens?|quota|limit(ed|s)?|cap(ped)?|ran out|too few|not enough "
     r"(credits|minutes|seats|words)|usage limit|throttl\w+|restrict\w+|only \d+ (credits|minutes))\b"),
    ("feature_gap", "Missing feature / promise gap",
     # `lacks?` carries a negative lookahead: "lack of customer service/support" is a
     # support complaint, not a feature gap, and was inflating this theme.
     r"\b(missing|lacks?(?!\s+of\s+(customer\s+)?(service|support|responsiveness|transparency|"
     r"communication|documentation))|no (drag[- ]and[- ]drop|way to|option to|ability to|support for)|"
     r"doesn'?t (include|support|offer|have)|does not (include|support)|wish it had|"
     r"should (have|include)|not included|advertised|promised|false advertising|"
     r"feature set.{0,20}(lousy|limited|poor|weak))\b"),
    ("usability_ui", "Hard to use / poor UI",
     r"\b(confusing|hard to (use|navigate|find)|difficult to (use|navigate)|steep learning curve|"
     r"poor (ui|ux|interface|design)|unintuitive|not intuitive|clunky|frustrating|complicated|"
     r"overwhelming|bad (ui|ux|interface)|buttons? (overlap|confus))\b"),
    ("reliability", "Unreliable / slow",
     r"\b(slow|lag(s|gy)?|timeout|time out|unreliable|inconsistent|downtime|intermittent|"
     r"sometimes works|flaky|freez\w+|hangs?|takes forever|long time to load)\b"),
    ("value_price", "Poor value for price",
     r"\b(overpriced|not worth|waste of money|better (free|alternative)|cheaper (alternative|"
     r"elsewhere)|free (alternative|version|tool)|too expensive|rip[- ]?off|save your money|"
     r"not worth (the|it|paying))\b"),
    ("setup_onboarding", "Setup / onboarding / docs",
     r"\b(set ?up|install\w*|configur\w*|onboarding|documentation|docs (are|were)|instructions|"
     r"tutorial|hard to (set up|install|configure)|complicated to set)\b"),
    ("integration", "Integration / API / export issues",
     # `import`/`export` are word-bounded with explicit suffixes: bare `import\w*` also
     # matched "important"/"importance". Bare `connect\w*` was dropped entirely - it
     # matched unrelated senses (e.g. a privacy complaint about connecting accounts).
     r"\b(integrat\w*|api|apis|webhooks?|zapier|make\.com|n8n|"
     r"export(s|ed|ing|able)?|import(s|ed|ing|able)?|"
     r"sync(s|ed|ing|roniz\w*)?|does ?n[o']?t (sync|connect|export))\b"),
]

QUESTION_THEMES = [
    ("license_scope", "License scope / commercial use",
     r"\b(commercial use|client(s)?|agency|white ?label|resell|resale|my customers|"
     r"how many (users?|seats?|sites?|domains?)|per (user|site|domain|client)|team size)\b"),
    ("limits_math", "Credit / limit math",
     r"\b(how many (credits?|minutes?|words?|emails?|images?)|credits? per|per month|"
     r"monthly limit|what (are|is) the limits?|enough for|run out|rollover|reset)\b"),
    ("feature_inclusion", "Is X actually included?",
     r"\b(is .{0,40} included|does it (do|support|have|include)|can (i|it|you) .{0,40}\?|"
     r"do you (support|offer|have)|will it (work|support)|included in (this|tier))\b"),
    ("deal_parity", "Deal vs paid-plan parity",
     r"\b(paid plan|regular plan|your website|full version|pro version|same as|difference between|"
     r"restricted|limited version|upgrade (to|later)|what'?s (the )?catch|compared to (the )?"
     r"(paid|regular|pro))\b"),
    ("competitor", "Competitor comparison",
     r"\b(vs\.?|versus|compare|alternative to|difference (from|between)|better than|"
     r"how (is|does) it (compare|differ))\b"),
    ("tech_reqs", "Technical requirements / hosting",
     r"\b(self[- ]?host|wordpress|requirements|compatible|browser|mac|windows|linux|"
     r"install|server|docker|api key|byok|openai key|gdpr|data (stored|residency|privacy))\b"),
    ("longevity", "Lifetime really lifetime?",
     r"\b(lifetime|forever|how long|what (happens|if) (if |when )?(you|the company|they) "
     r"(shut|stop|sell)|guarantee|future updates|roadmap)\b"),
    ("refund_q", "Refund / guarantee",
     r"\b(refund|money back|guarantee|trial|test (it|before)|cancel)\b"),
]

# Positive-review taxonomy. Built by reading ~4,600 real 4-5 star reviews beside each
# vendor's own value_prop. The last two entries are NOT praise - they flag reviews that
# cannot corroborate the promise, which matters because a 5-star rating alone overstates
# verified satisfaction (many are written before the buyer has used the product).
POS_THEMES = [
    ("delivers_promise", "Explicitly confirms it does the promised job",
     r"\b(delivers? on (its|their|the) promise|does (exactly )?what it (says|claims|promises)|"
     r"works as (described|advertised|expected)|as advertised|exactly as (described|promised)|"
     r"lives? up to|does the job|did the job|truly delivers|promised and delivered|"
     r"it (really )?works|works like a charm|does what i (need|want))\b"),
    ("beats_alternative", "Compared favourably against a rival / prior tool",
     r"\b(better than|tried .{0,40}(but|before)|compared to|instead of .{0,30}(using|paying)|"
     r"switched from|moved from|miles ahead|couldn'?t even get close|other tools|"
     r"(alternative|competitor)s? (never|didn'?t|could ?n[o']?t)|i'?ve (tried|used) .{0,40}(years?|others?))\b"),
    ("replaces_subscription", "Cancelled a subscription for this lifetime deal",
     r"(cancel\w*[^.]{0,30}\b(subscription|monthly (fee|plan|cost|payment))|"
     r"no (more )?(monthly|recurring)\b[^.]{0,18}(fee|fees|cost|costs|charge|charges|payment|"
     r"subscription|bill)|"
     r"(instead|rather) than (paying|a|the) (monthly|subscription|recurring)|"
     r"ditch\w*[^.]{0,28}subscription|one[- ]?time (payment|fee|price|purchase|cost)|"
     r"no subscription(s)? (fee|needed|required|at all)|without (a |any )?subscription)"),
    ("value_price", "Good value for the price",
     r"\b(worth (every|the|it)|great (value|deal|price)|amazing (deal|value|for the price)|"
     r"value for money|unbeatable|bargain|steal|can'?t beat (the|this) price|for the price|"
     r"so (cheap|affordable)|best (deal|value)|price is (right|great|amazing))\b"),
    ("ease_speed", "Easy to use / fast time-to-value",
     r"\b(easy to (use|set ?up|install|learn|get started|navigate)|very easy|super easy|"
     r"intuitive|user[- ]friendly|straightforward|simple to (use|set ?up)|no (steep )?learning curve|"
     r"within (minutes|an hour|a few minutes)|took me \d+ minutes?|up and running (quickly|in no time)|"
     r"plug and play|effortless|seamless(ly)?|beginner[- ]friendly)\b"),
    ("support_good", "Support / founder responsiveness praised",
     r"\b(support (is|was|has been) (great|amazing|excellent|responsive|fast|quick|outstanding|"
     r"fantastic|superb|helpful)|respond(ed|s) (quickly|fast|within|in \d+)|repl(y|ied) (quickly|fast|"
     r"within|in \d+)|fixed (it|within|in \d+)|responsive (team|support|founder)|"
     r"(team|founder|ceo|developer) (is|was) (very )?(responsive|helpful|great|amazing|hands[- ]on)|"
     r"great (customer )?(service|support)|excellent (customer )?(service|support)|"
     r"went (above and )?beyond|helped me (set ?up|with|through))\b"),
    ("works_reliably", "Works reliably / no problems",
     r"\b(works? (perfectly|flawlessly|great|well|like a charm|every time|consistently)|"
     r"no (issues|problems|bugs|complaints|hiccups)|flawless|reliable|rock[- ]solid|stable|"
     r"hasn'?t (crashed|failed)|zero (issues|problems)|performs? well|never (fails|crashed))\b"),
    ("saves_time", "Saves time / automates the chore",
     r"\b(saves? (me |us )?(so much |a lot of |lots of |hours?|time|days?)|time[- ]saver|"
     r"(saved|cut|reduced) (me |us )?(hours?|time|days?)|automat\w+ (my|our|the|so much)|"
     r"(boosted|increased|improved) (my |our )?(productivity|efficiency|output)|"
     r"streamlin\w+|frees? up (my |our )?time|no more manual|manual work (gone|eliminated))\b"),
    ("output_quality", "Output quality / results impressed",
     r"\b(high quality|top[- ]notch|excellent (results?|quality|output)|impressive (results?|output|"
     r"quality)|accurate|professional (results?|looking|output)|blew me away|blown away|amazed|"
     r"stunning|beautiful(ly)?|great (results?|output|quality)|really good (results?|output)|"
     r"quality is (great|excellent|amazing|superb|impressive))\b"),
    ("non_technical_ok", "Accessible to a non-technical user",
     r"\b(not (very )?(technical|tech[- ]savvy)|no (coding|code|technical (skills?|background))|"
     r"don'?t (know|understand) (how to )?cod\w+|far away from coding|even (i|a beginner|someone "
     r"(like me|non[- ]technical))|as a (beginner|non[- ]technical|marketer|attorney|teacher|"
     r"small business)|without (any )?(coding|technical (knowledge|skills)))\b"),
    ("updates_roadmap", "Active development / updates valued",
     r"\b(regular updates|frequent updates|constant(ly)? (updat|improv)\w+|new features "
     r"(regularly|constantly|often)|actively (developed|maintained|improved|updated)|"
     r"roadmap|listens? to (feedback|customers|users)|responsive to (feedback|suggestions)|"
     r"(keeps?|keeping) (it )?updat\w+|improving (it|constantly|regularly))\b"),
    # --- NOT corroboration: flag these so satisfaction isn't overstated
    ("anticipatory", "ANTICIPATORY — written before real use",
     r"\b(just (bought|purchased|got|started|signed up|received)|haven'?t (yet )?(had the chance|"
     r"tried|used|tested|explored)|yet to (try|use|test)|can'?t wait (to|for)|looking forward to "
     r"(using|trying|testing)|so far (so good|it|,)|will update (this |my )?review|"
     r"(excited|eager) to (try|use|test|start|see)|first impressions?|only (just )?(started|used) "
     r"it|barely (started|used|scratched)|initial (thoughts|impressions?))\b"),
    ("qualified_praise", "Praise carrying an explicit caveat",
     # Deliberately narrow. A bare "however"/"though"/"but it" is a discourse marker and
     # often introduces MORE praise ("However it has a lot more uses than just Real Estate"),
     # so counting those inflated this theme to 28% of all positive reviews. Only explicit
     # caveat constructions are counted now.
     r"(my only (complaint|issue|concern|gripe|criticism|downside|regret|problem)|"
     r"(one|the only|a single) (downside|drawback|negative|con|caveat|complaint|issue|criticism)|"
     r"(minor|small|few|some) (issue|issues|problem|problems|complaint|complaints|gripe|gripes|"
     r"quirk|quirks|limitation|limitations|shortcoming|shortcomings)|"
     r"wish (it|they|there|these) (had|would|could|were|was|did)|"
     r"could (be|use|do with|stand) (better|improvement|improved|more|some)|"
     r"(room|scope) for improvement|not (perfect|ideal|without (its|their) (flaws?|issues?))|"
     r"unfortunately|that (said|being said)|only (complaint|issue|downside|problem|criticism)|"
     r"(but|however|although)[^.]{0,40}(lacks?|missing|wish|hope they|could be better|"
     r"a bit (slow|confusing|clunky|limited)|disappoint|frustrat|annoying|doesn'?t (work|support)|"
     r"needs (work|improvement)))"),
]

STOP = set("""the a an and or but if then than that this these those is are was were be been being
of to in for on with at by from as into about it its it's i we you he she they me my your our their
not no yes do does did done have has had having will would can could should may might must shall so
very just also more most other some any all each every only own same too s t don now""".split())


def compile(themes):
    # re.I only. Do NOT add re.X: verbose mode strips unescaped whitespace from the
    # pattern, which silently breaks every multi-word phrase ("no response" -> "noresponse").
    return [(slug, label, re.compile(pat, re.I)) for slug, label, pat in themes]


PAIN = compile(PAIN_THEMES)
QUES = compile(QUESTION_THEMES)
POSC = compile(POS_THEMES)
# themes that mean "the product does not do the job it was sold to do"
PROMISE_FAIL = {"feature_gap", "deal_devalued", "broken"}
# themes that mean "the job is right, the delivery around it failed"
EXEC_FAIL = {"support_unresponsive", "refund_friction", "reliability", "usability_ui",
             "setup_onboarding", "limits_credits"}


def load_jsonl(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def tag(text, table):
    hits = []
    for slug, label, rx in table:
        m = rx.search(text)
        if m:
            hits.append((slug, label, m.group(0).lower(), m.start()))
    return hits


def excerpt(text, start, width=150):
    """Window centred on the match, so a displayed quote always contains its own
    trigger word. Truncating to the first N chars can cut the match off entirely,
    which would show a quote under a theme heading it visibly doesn't support."""
    a = max(0, start - width)
    b = min(len(text), start + width)
    return ("…" if a > 0 else "") + re.sub(r"\s+", " ", text[a:b]).strip() + ("…" if b < len(text) else "")


def main():
    master = json.load(open(os.path.join(HERE, "appsumo_all_products.json")))
    details = {r["id"]: r for r in load_jsonl("details.jsonl")}
    pages = {r["slug"]: r for r in load_jsonl("pages.jsonl")}
    reviews = {r["deal_id"]: r for r in load_jsonl("reviews.jsonl")}
    positive = {r["deal_id"]: r for r in load_jsonl("positive.jsonl")}
    # browse payload carries active_codes (the sales signal); details does not.
    # NOTE: _raw_checkpoint.json is a JSON *array* (one line), not JSONL.
    raw = json.load(open(os.path.join(HERE, "_raw_checkpoint.json")))
    browse = {}
    for r in raw:
        for d in r["deals"]:
            browse[d["id"]] = d

    print(f"loaded: master={len(master['products'])} details={len(details)} "
          f"pages={len(pages)} reviews={len(reviews)} browse={len(browse)}", file=sys.stderr)

    products = []
    theme_totals = collections.Counter()
    qtheme_totals = collections.Counter()
    pos_theme_totals = collections.Counter()
    theme_quotes = collections.defaultdict(list)
    pos_quotes_global = collections.defaultdict(list)

    for p in master["products"]:
        did, slug = p["deal_id"], p["slug"]
        det = details.get(did, {})
        pg = pages.get(slug, {})
        rv = reviews.get(did, {})
        bw = browse.get(did, {})

        # ---- tier ladder / willingness to pay
        plans = sorted([x for x in (pg.get("plans") or []) if not x.get("is_plus_tier")],
                       key=lambda x: x.get("tier") or 0)
        prices = [float(x.get("price") or 0) for x in plans]
        prices = [x for x in prices if x > 0]
        ladder = [{"tier": x.get("tier"), "price": float(x.get("price") or 0),
                   "original": float(x.get("original_price") or 0),
                   "plan_type": x.get("plan_type")} for x in plans]
        shape = None
        if len(prices) >= 3:
            step = prices[1] - prices[0]
            shape = ("linear" if all(abs((prices[i + 1] - prices[i]) - step) < 0.51
                                     for i in range(len(prices) - 1)) else "progressive")

        # ---- features
        core = [{"feature": f.get("feature"), "tooltip": f.get("tooltip")}
                for f in (det.get("core_features") or []) if f.get("feature")]
        common = [f.get("text") for f in (det.get("common_features") or []) if f.get("text")]
        terms = [t.get("text") for t in (det.get("default_plan_terms") or []) if t.get("text")]
        plan_by_id = {x.get("id"): x.get("tier") for x in plans}
        matrix = []
        for f in (det.get("dealfeatures") or []):
            ent = {}
            for e in (f.get("entries") or []):
                t = plan_by_id.get(e.get("plan_id"))
                if t is not None:
                    ent[str(t)] = e.get("entry")
            matrix.append({"feature": f.get("feature"), "by_tier": ent,
                           "tooltip": f.get("tooltip")})

        # ---- sales volume
        ac, cr = bw.get("active_codes"), bw.get("codes_remaining")
        sold = method = None
        if ac and cr is not None and ac > cr >= 0:
            sold, method = ac - cr, "codes"
        elif bw.get("freebie_downloads_total"):
            sold, method = bw["freebie_downloads_total"], "downloads"
        rc = (det.get("deal_review") or {}).get("review_count") or 0
        dr = det.get("deal_review") or {}
        stars = {str(k): int(dr.get(f"review_count_{k}_tacos") or 0) for k in range(1, 6)}

        entry = prices[0] if prices else (p.get("price_usd") or 0)
        top = prices[-1] if prices else entry

        # ---- painpoints from review text
        texts = []
        for k, b in (rv.get("buckets") or {}).items():
            for c in (b.get("comments") or []):
                t = (c.get("comment") or "").strip()
                if t:
                    texts.append((int(k), t, c.get("up_votes") or 0, c.get("title") or ""))
        themes = collections.Counter()
        quotes = []
        pq = collections.defaultdict(list)
        for star, t, up, title in texts:
            hit = tag(t, PAIN)
            for slug_, label, matched, pos in hit:
                themes[slug_] += 1
                theme_totals[slug_] += 1
                rec = {"theme": slug_, "star": star, "up": up,
                       "text": re.sub(r"\s+", " ", t)[:300],
                       "ctx": excerpt(t, pos), "matched": matched}
                theme_quotes[slug_].append({"product": p["name"], **rec})
                pq[slug_].append(rec)
            if not hit and len(t) > 60:
                pq["_untagged"].append({"theme": "_untagged", "star": star, "up": up,
                                        "text": re.sub(r"\s+", " ", t)[:300],
                                        "ctx": None, "matched": None})
        # keep the most useful quotes per product per theme (upvotes, then length)
        pain_quotes = []
        for slug_, lst in pq.items():
            lst.sort(key=lambda q: (-q["up"], -len(q["text"])))
            pain_quotes.extend(lst[:3])
        pain_quotes.sort(key=lambda q: (-q["up"], -len(q["text"])))
        top_themes = [{"theme": s, "n": n} for s, n in themes.most_common()]
        neg_total = len(texts)

        # ---- pre-purchase questions
        qtexts = [((c.get("title") or "") + " " + (c.get("comment") or "")).strip()
                  for c in (rv.get("questions") or [])]
        qtexts = [re.sub(r"\s+", " ", t) for t in qtexts if t]
        qthemes = collections.Counter()
        for t in qtexts:
            for slug_, label, matched, pos in tag(t, QUES):
                qthemes[slug_] += 1
                qtheme_totals[slug_] += 1

        # ---- the vendor's own promise (what the product purports to serve)
        sd = bw.get("story_details") or {}
        promise = {
            "value_prop": (sd.get("value_prop") or "").strip(),
            "subheader": (sd.get("subheader") or "").strip(),
            "highlights": [re.sub(r"\s+", " ", h.get("highlight") or "").strip()
                           for h in sorted(bw.get("story_highlights") or [],
                                           key=lambda x: x.get("order") or 0)
                           if h.get("highlight")],
            "tagline": (p.get("tagline") or "").strip(),
            "serves": [c.strip() for c in ((p.get("best_for") or "").split(",") if p.get("best_for") else []) if c.strip()],
            "replaces": [a.strip() for a in ((p.get("alternative_to") or "").split(",") if p.get("alternative_to") else []) if a.strip()],
            "use_cases": [c.strip() for c in ((p.get("features") or "").split(",") if p.get("features") else []) if c.strip()],
        }

        # ---- positive reviews: does the delivered experience match the promise?
        pv = positive.get(did, {})
        ptexts = []
        for k, b in (pv.get("buckets") or {}).items():
            for c in (b.get("comments") or []):
                t = (c.get("comment") or "").strip()
                if t:
                    ptexts.append((int(k), re.sub(r"\s+", " ", t), c.get("up_votes") or 0))
        pos_themes = collections.Counter()
        ppq = collections.defaultdict(list)
        for star, t, up in ptexts:
            hit = tag(t, POSC)
            for slug_, label, matched, pos_ in hit:
                pos_themes[slug_] += 1
                pos_theme_totals[slug_] += 1
                rec = {"theme": slug_, "star": star, "up": up, "text": t[:280],
                       "ctx": excerpt(t, pos_), "matched": matched}
                pos_quotes_global[slug_].append({"product": p["name"], **rec})
                ppq[slug_].append(rec)
        pos_quotes = []
        for slug_, lst in ppq.items():
            lst.sort(key=lambda q: (-q["up"], -len(q["text"])))
            pos_quotes.extend(lst[:3])
        pos_quotes.sort(key=lambda q: (-q["up"], -len(q["text"])))

        # ---- promise-fulfilment metrics.
        # satisfaction_rate uses the COMPLETE star breakdown (not the 20-record sample),
        # so it is exact; the text-derived shares below are sample-based.
        st = {int(k): v for k, v in stars.items()}
        n_all = sum(st.values())
        satisfaction = round((st.get(4, 0) + st.get(5, 0)) * 100 / n_all, 1) if n_all else None
        n_pos = len(ptexts)
        antic = pos_themes.get("anticipatory", 0)
        qual = pos_themes.get("qualified_praise", 0)
        # corroborated = positive reviews that actually affirm something, i.e. not
        # purely anticipatory and not merely qualified
        corroborated = max(0, n_pos - antic)
        fulfillment = {
            "reviews_total": n_all,
            "satisfaction_rate": satisfaction,
            "stars_1_2_pct": round((st.get(1, 0) + st.get(2, 0)) * 100 / n_all, 1) if n_all else None,
            "pos_analyzed": n_pos,
            "pos_expected": st.get(4, 0) + st.get(5, 0),
            "pos_coverage_pct": round(n_pos * 100 / (st.get(4, 0) + st.get(5, 0)), 1)
                              if (st.get(4, 0) + st.get(5, 0)) else None,
            "explicit_delivers": pos_themes.get("delivers_promise", 0),
            "anticipatory": antic,
            "anticipatory_pct": round(antic * 100 / n_pos, 1) if n_pos else None,
            "qualified": qual,
            "qualified_pct": round(qual * 100 / n_pos, 1) if n_pos else None,
            "corroborated": corroborated,
            "promise_fail_neg": sum(v for k_, v in themes.items() if k_ in PROMISE_FAIL),
            "exec_fail_neg": sum(v for k_, v in themes.items() if k_ in EXEC_FAIL),
        }
        fulfillment["promise_fail_pct"] = (round(fulfillment["promise_fail_neg"] * 100 / neg_total, 1)
                                           if neg_total else None)

        capped = rv.get("capped") or []
        products.append({
            **{k: p.get(k) for k in ["name", "slug", "url", "tagline", "group", "category",
                                     "subcategory", "listing", "plan_types", "is_free",
                                     "price_usd", "original_price_usd", "discount_pct",
                                     "plus_price_usd", "rating", "reviews", "start_date",
                                     "end_date", "alternative_to", "best_for", "features",
                                     "review_summary", "categories"]},
            "deal_id": did,
            "product_url": det.get("product_url") or pg.get("product_url"),
            "availability": det.get("availability"),
            "refundable_days": det.get("refundable_days"),
            "comment_count": (det.get("deal_comment") or {}).get("comment_count"),
            "plan_stack_count": det.get("plan_stack_count"),
            # willingness to pay
            "tier_count": len(prices), "entry_price": entry, "top_price": top,
            "wtp_ratio": round(top / entry, 1) if entry and top and top > entry else None,
            "ladder_shape": shape, "ladder": ladder,
            "plus_tiers": [x for x in (pg.get("plans") or []) if x.get("is_plus_tier")],
            # features
            "core_features": core, "common_features": common, "plan_terms": terms,
            "feature_matrix": matrix,
            # sales
            "sold_estimate": sold, "sales_method": method,
            "active_codes": ac, "codes_remaining": cr,
            "review_count": rc, "stars": stars,
            "est_revenue_at_entry": round(sold * entry) if sold and entry else None,
            # painpoints
            "neg_reviews_analyzed": neg_total,
            "neg_reviews_expected": sum(stars[k] for k in ("1", "2", "3")),
            "review_fetch_capped": capped,
            "pain_themes": top_themes,
            "pain_quotes": pain_quotes[:12],
            "questions_total": rv.get("questions_total"),
            "questions_sampled": len(qtexts),
            "questions_sample": [t[:260] for t in qtexts[:5]],
            "question_themes": [{"theme": s, "n": n} for s, n in qthemes.most_common()],
            "promise": promise,
            "pos_themes": [{"theme": s, "n": n} for s, n in pos_themes.most_common()],
            "pos_quotes": pos_quotes[:10],
            "fulfillment": fulfillment,
        })

    # best quotes per theme (most upvoted, then longest)
    for s in theme_quotes:
        theme_quotes[s].sort(key=lambda q: (-q["up"], -len(q["text"])))
        theme_quotes[s] = theme_quotes[s][:12]
    for s in pos_quotes_global:
        pos_quotes_global[s].sort(key=lambda q: (-q["up"], -len(q["text"])))
        pos_quotes_global[s] = pos_quotes_global[s][:12]

    pos_analyzed = sum(p["fulfillment"]["pos_analyzed"] for p in products)
    out = {
        "generated_from": ["appsumo_all_products.json", "details.jsonl", "pages.jsonl",
                           "reviews.jsonl", "positive.jsonl", "_raw_checkpoint.json"],
        "product_count": len(products),
        "pos_analyzed": pos_analyzed,
        "sales_method_counts": dict(collections.Counter(p["sales_method"] for p in products)),
        "pain_theme_labels": {s: l for s, l, _ in PAIN_THEMES},
        "question_theme_labels": {s: l for s, l, _ in QUESTION_THEMES},
        "pos_theme_labels": {s: l for s, l, _ in POS_THEMES},
        "pain_theme_totals": dict(theme_totals.most_common()),
        "question_theme_totals": dict(qtheme_totals.most_common()),
        "pos_theme_totals": dict(pos_theme_totals.most_common()),
        "theme_quotes": dict(theme_quotes),
        "pos_theme_quotes": dict(pos_quotes_global),
        "products": products,
    }
    json.dump(out, open(os.path.join(HERE, "analysis.json"), "w"), ensure_ascii=False)
    print(f"\nwrote analysis.json: {len(products)} products, "
          f"{os.path.getsize(os.path.join(HERE,'analysis.json'))//1024} KB", file=sys.stderr)
    print("sales_method:", out["sales_method_counts"], file=sys.stderr)
    labels = {s: l for s, l, _ in PAIN_THEMES}
    print("\npainpoint themes (review mentions):", file=sys.stderr)
    for s, n in theme_totals.most_common():
        print(f"   {n:>5}  {labels[s]}", file=sys.stderr)
    qlabels = {s: l for s, l, _ in QUESTION_THEMES}
    print("\nquestion themes:", file=sys.stderr)
    for s, n in qtheme_totals.most_common():
        print(f"   {n:>5}  {qlabels[s]}", file=sys.stderr)
    plabels = {s: l for s, l, _ in POS_THEMES}
    print(f"\npositive-review themes (across {pos_analyzed} 4-5* reviews):", file=sys.stderr)
    for s, n in pos_theme_totals.most_common():
        pct = n * 100 / pos_analyzed if pos_analyzed else 0
        print(f"   {n:>5} ({pct:>4.1f}%)  {plabels[s]}", file=sys.stderr)


if __name__ == "__main__":
    main()
