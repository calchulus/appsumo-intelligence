"""Summary-tab prose for the AppSumo dashboard.

Every number here is computed in analyze.py / crossref.py and asserted against the embedded
payload by test_dashboard.py, so the prose cannot silently drift from the data.
"""

TAKEAWAYS = """
<div class="tk"><div class="tkn">1</div><div>
  <h4>The softest claims fail hardest; the hardest ones hold</h4>
  <p>“Easy / simple / seamless” is contradicted by customers in <b>33%</b> of the products that
  claim it, and “all-in-one / replace N tools” in <b>29%</b>. “Lifetime access” — the boldest
  promise on the marketplace — is contradicted in only <b>2%</b>. Vague adjectives are unfalsifiable
  at purchase and disappointing in use; checkable claims mostly get delivered.</p>
  <span class="ev">Evidence: <b>Claims vs complaints</b> tab. 101 of 342 products have ≥1
  contradicted claim, across 310 negative reviews.</span></div></div>

<div class="tk"><div class="tkn">2</div><div>
  <h4>Complaints are delivery failures, not feature requests</h4>
  <p>The top four themes are all about the gap between listing and product: missing feature /
  promise gap <b>19.6%</b>, broken <b>18.5%</b>, refund sought <b>17.5%</b>, limits too tight
  <b>17.2%</b>. Support is only 6.9% — but it is the hinge. The recurring sequence in the text is
  <em>product broke → support silent → refund</em>.</p>
  <span class="ev">Evidence: <b>Insights</b> tab, from 2,389 negative reviews (86% of all 1–3★
  reviews on the site).</span></div></div>

<div class="tk"><div class="tkn">3</div><div>
  <h4>High satisfaction, thin corroboration</h4>
  <p>Median satisfaction is <b>89.8%</b> — but only <b>6.3%</b> of positive reviews actually say the
  product did the job it was sold to do, versus <b>23.3%</b> that praise how easy it was. Only
  <b>165 of 250</b> judgeable products have even one buyer explicitly confirming the outcome.
  A further <b>5.7%</b> of positive reviews are anticipatory, written before real use.</p>
  <span class="ev">Evidence: <b>Promise vs delivery</b> tab, from 5,819 positive reviews.</span></div></div>

<div class="tk"><div class="tkn">4</div><div>
  <h4>Volume is brutally concentrated, and the biggest mover isn’t a sale</h4>
  <p>622,571 derived paid units across 174 products, but the median is <b>1,372</b> while the top
  five hold roughly a fifth of it. The single largest number on the site — 66,456 — is a
  <em>free</em> lead magnet. Revenue leaders are WordHero (~$3.1M), Reoon Email Verifier (~$2.1M)
  and Switchy (~$1.7M).</p>
  <span class="ev">Evidence: <b>Insights</b> tab. Paid units and free downloads are kept in separate
  rankings on purpose.</span></div></div>

<div class="tk"><div class="tkn">5</div><div>
  <h4>Willingness to pay is a stacking game, not a value estimate</h4>
  <p>Median top-tier is <b>5×</b> entry, max <b>61×</b>. But 94 products run a <em>linear</em>
  ladder — flat price per added code — meaning the marginal buyer is an agency stacking identical
  licences, not a bigger company paying for more capability. That is a distribution channel, not a
  pricing strategy. Only 89 progressive ladders are genuinely segmenting by buyer size, and 159
  products have too few priced tiers to classify either way.</p>
  <span class="ev">Evidence: <b>Insights</b> tab, from 1,057 tier rows across all 342 products.</span></div></div>

<div class="tk"><div class="tkn">6</div><div>
  <h4>Ceiling price says nothing about revenue</h4>
  <p>LeadOcean lists a $1,999 top tier against <b>1</b> derived unit sold. The high-ceiling,
  high-volume combination is rare and specific: FlipLink.me ($1,290 top, ~4,000 units) and
  XInterview AI ($890 top, ~4,500 units) are the ones actually converting the ladder.</p>
  <span class="ev">Evidence: <b>Insights</b> tab, ceiling-vs-entry table.</span></div></div>

<div class="tk"><div class="tkn">7</div><div>
  <h4>What wins is unglamorous and narrow</h4>
  <p>The top sellers are link-in-bio, AI content writing, email verification, spreadsheet templates
  and business courses — recurring manual chores removed for under $90. The AI products that sold are
  AI <em>applied to an existing chore</em>, not AI as the product. The best-evidenced performers make
  narrow, one-session-verifiable promises: Reoon (“protect your email server’s reputation”, 98.5%
  satisfaction, 756 reviews) and Switchy (“boost conversions with retargeting links”, 96.7%).</p>
  <span class="ev">Evidence: <b>Promise vs delivery</b> tab, best-evidenced fulfilment table.</span></div></div>

<div class="tk"><div class="tkn">8</div><div>
  <h4>Deal devaluation is AppSumo’s own structural risk</h4>
  <p><b>3.2%</b> of negative reviews complain that the current offer is worse than an earlier one for
  the same product — “stripped things down and still charge more.” Small share, but distinctive: the
  anger is aimed at the <em>marketplace’s</em> repricing, not the vendor’s product, and it lands on
  the repeat buyers who are AppSumo’s core audience.</p>
  <span class="ev">Evidence: <b>Insights</b> tab, deal_devalued theme with verbatim quotes.</span></div></div>

<div class="tk"><div class="tkn">9</div><div>
  <h4>Pre-purchase questions show where listings fail to answer</h4>
  <p>Buyers repeatedly ask things the listing should settle: “is lifetime really lifetime”
  <b>8.3%</b>, commercial / client / white-label scope <b>8.1%</b>, and how the deal differs from the
  vendor’s public paid plan <b>4.6%</b>. That last one is a trust signal — buyers suspect the AppSumo
  tier is cut-down, and several reviews confirm it after purchase.</p>
  <span class="ev">Evidence: <b>Insights</b> tab, from 5,841 pre-purchase questions.</span></div></div>
"""

SOWHAT = """
<div class="note ok"><b>If you are buying on AppSumo:</b> the star rating barely discriminates —
median satisfaction is 89.8% — so don't use it as your primary signal. Sort by
<em>explicit “does the job”</em> confirmations and check the anticipatory share. A 4.6★ with 200
reviews written in the first week is weaker evidence than a 4.9★ whose reviewers name the outcome.
Then cross-check the specific claims: if a product promises “all-in-one” or “seamless”, assume
roughly a one-in-three chance a buyer contradicts it.</div>

<div class="note ok"><b>If you are selling here:</b> make the promise narrow and verifiable in one
session — that is what produces corroborating reviews, which is what converts. Avoid “all-in-one”
and “effortless”, the two most-contradicted claim types. Do promise concrete, checkable things
(lifetime access; “unlimited” with the real limit stated), because those are the claims that hold.
Price the ladder progressively if you want size segmentation — a 10-tier linear ladder just sells
ten codes to one agency.</div>

<div class="note"><b>If you are assessing the marketplace itself:</b> the binding constraint is
listing accuracy, not product quality. 27 buyers state outright that the listing did not match the
product, and promise-focused complaints (42% median share of negatives) are the kind that end in
refunds. The 17.5% refund-language rate is the number to watch.</div>
"""

CONFIDENCE = """
<div class="note ok"><b>Exact, not estimated:</b> the product catalogue (342/342 reconciled against
AppSumo's own site-wide count, every product's embedded taxonomy verified against the category it
was fetched under), tier ladders (1,057 rows), star ratings and satisfaction rates (complete star
breakdowns, which reconcile with the reported average rating for all 342 products), and prices.</div>

<div class="note"><b>Derived, validated:</b> units sold = <code>active_codes − codes_remaining</code>.
Validated on the 6 freebies that publish a true download count: <b>0.3% median error</b>, worst 1.7%.
It covers only 174 of 342 products — the other 133 use no code system and are ranked separately by
review count, never blended in. Revenue is a <b>floor</b>: units × entry-tier price, ignoring
tier-ups and AppSumo's cut.</div>

<div class="note"><b>Sampled:</b> negative review text covers 86% of all 1–3★ reviews on site
(excellent), but positive text only <b>26%</b> of 4–5★ reviews, because the API hard-caps every
rating bucket at 20 records. Questions are the 20 most recent per product (5,841 of 21,832). So
praise-theme percentages describe a sample of <em>recent</em> positive reviews — directional only.</div>

<div class="note"><b>Pattern-matched, then audited:</b> all theme and contradiction counts come from
regex tagging, so they are <b>mentions, not complaints</b>. Every displayed quote shows the exact
trigger token and a match-centred excerpt so you can judge each call yourself. Four tagging bugs were
found by reading matched substrings and fixed: <code>re.X</code> silently stripping whitespace
(undercounted support themes ~5×); <code>import\\w*</code> matching “important”; bare
<code>limited</code> matching “limited expectations”, which inflated the unlimited-contradiction rate
from a true 14% to a bogus 38%; and bare <code>expired</code> matching a cookie error and an OAuth
session lapse. Residual known weakness: for chat-widget vendors (AnyChat, Support Board) “live chat”
is the product rather than their support, so 2 of 6 support-claim contradictions are semantic
mismatches.</div>

<div class="note"><b>Source-data problems found:</b> AppSumo's FAQs for <em>Switchy</em> (a
Bitly/Linktree competitor) describe a Bangalore smart light-switch retrofit — “5 minutes for a
trained electrician”, “Is WiFi mandatory?” — so that product's FAQ text is excluded from claim
detection, on evidence rather than by heuristic (a vocabulary-overlap detector was built and
rejected: Switchy scores above the 5th percentile, so no threshold catches it without also flagging
nine legitimate products). AppSumo's own boilerplate plan terms (“An AppSumo Original, created by the
AppSumo team as a simple, affordable solution”) were fabricating vendor claims; 14 such strings are
now filtered. <code>would_recommend</code> is collected but 0 across all 342 products, so it could not
be used. Plus-exclusive variants (Screpy / Screpy-Plus) share the parent's reviews byte-for-byte and
would double-count in any “best-reviewed” ranking.</div>
"""


CAMPAIGN_LESSONS = """
<p>These are drawn from two things AppSumo publishes that most analyses miss: the
<code>participation</code> list (every promotional campaign each product appeared in — 75 campaigns,
2021–2026) and the per-tier <code>codes</code> field (how many licences one purchase grants). Every
figure below is measured across all 342 live listings as of 2026-10-26.</p>

<p><strong>1. You are launching an annuity, not a spike.</strong> The median listing has been live
<strong>1,276 days — 3.5 years</strong> — and all 203 products that publish inventory are still live.
Only one product in the top 15 by revenue velocity has been listed for under 120 days: FuseBase, at
$1,975/day over 19 days. Everything else earning well is earning slowly for years. WordHero grosses
$1,607/day, but across 1,932 days. Plan support, roadmap and hosting for a multi-year commitment,
not a 72-hour launch.</p>

<p><strong>2. Revenue is concentrated, but less than you'd fear.</strong> The top 5 listings are
<strong>31%</strong> of measured gross revenue and the top 20 are <strong>59%</strong> — so 41% sits
in the long tail of ~148 listings. Total measured gross is <strong>$30.38M</strong> across 168 paid
campaigns (497,195 codes). The floor–ceiling range is only $30.378M–$30.387M, because 91 of the 93
multi-tier ladders are linear in price-per-code, which makes the estimate exact rather than
midpoint-guessed.</p>

<p><strong>3. Price per code, not per tier.</strong> <strong>93</strong> of the 168 paid campaigns
sell tiers granting more than one code per purchase (up to 10), and <strong>237</strong> listings
mention stacking explicitly. The buyer scaling up is an agency buying identical codes, not a larger
company buying more capability. A linear ladder ($49/$98/$147…) is the house style for exactly this
reason. If you build a progressive ladder, understand that you're segmenting by buyer size — only 2
paid campaigns do this while remaining linear per-code.</p>

<p><strong>4. The contract is uniform, and the two 60-day clocks are the thing to design around.</strong>
<strong>322 of 342</strong> listings carry a 60-day refund window and <strong>297</strong> impose a
60-day code-redemption deadline. They are the same length, so a buyer's refund right and their
activation deadline expire together. <strong>18 listings are non-refundable</strong> (0-day window)
— a choice with visible review consequences. Onboarding email should start the day the code is
issued, not the day the buyer feels ready.</p>

<p><strong>5. Include the plan-rename clause.</strong> <strong>107</strong> listings promise the
licence follows the product if the vendor renames the plan. It is the clause that makes a lifetime
deal survivable across a rebrand or repositioning — cheap to grant, and its absence is what turns a
pivot into an "access lost" complaint.</p>

<p><strong>6. Only 25 of 342 exclude existing customers.</strong> "New users only" is the exception,
not the norm. Assume your existing customer base will buy this deal, and decide in advance whether
that's a feature (upgrade path) or a problem (channel conflict with your SaaS pricing).</p>

<p><strong>7. Promotion depth is not a sales lever — but it does erode satisfaction.</strong> Raw
numbers look like a strong effect: median codes rise from 124 (one campaign) to 1,587 (24+). But that
is a tenure artifact — older listings have lived through more sales events. Controlling for launch
cohort, high-promotion products beat low-promotion ones on median volume in only
<strong>3 of 6</strong> cohorts, with no consistent direction. Satisfaction, however, is lower for
heavily-promoted products in <strong>6 of 6</strong> cohorts, and the gap widens for newer launches
(1.0 point in the 2021 cohort → 5.3 points in 2026). More exposure means more edge cases surfacing
in public.</p>

<p><strong>8. Counterintuitively, being in <em>every</em> sale protects you.</strong> "Deal devalued"
anger — buyers complaining the current offer is worse than an earlier one — is <strong>7.0%</strong>
of negative reviews for lightly-promoted products (0–5 campaigns) versus <strong>2.3%</strong> for
the always-on roster. Refund language follows the same gradient (23.5% → 16.1%), as does
missing-feature complaint (25.5% → 13.1%). If your product is only <em>sometimes</em> discounted,
the customers who paid more feel shortchanged when it reappears cheaper. Consistent discounting
removes the reference price to be angry about.</p>

<p><strong>9. Extended access is table stakes and DOTD is the real prize.</strong>
<strong>254</strong> products appear in both the general-access and extended-access audiences of the
same campaign; <strong>0</strong> are general-access-only and <strong>1</strong> extended-only. Don't
negotiate for extended access — assume you get both or neither. By contrast a Deal-of-the-Day slot is
genuinely scarce: <strong>24 products across 28 DOTD runs</strong>, versus Taco Day reaching
<strong>321</strong> products. Seasonal mega-sales are near-universal and therefore weak signals; a
DOTD is AppSumo actively betting on you.</p>

<p><strong>10. Volume and satisfaction are decoupled — and free skews both.</strong> Among the
always-on roster the three highest-volume, lowest-satisfaction products (VectorGrove 32,496 codes at
46.4%, ApproveMe's contract templates 51,311 at 47.5%, Intellifluence 45,420 at 50.0%) are
<em>all free lead magnets</em> — freebie grabbers rate harshly, and they are distribution, not
revenue. The worst-satisfaction <em>paid</em> always-on products are Domain Monitor (55.6%) and WP
Social (60.0%). Meanwhile Switchy proves the combination is achievable: 43,142 codes at
<strong>96.7%</strong> satisfaction on a $39 entry. That is the benchmark to aim at, not the raw
volume leaders.</p>

<p><strong>11. What a realistic first two years looks like.</strong> Of <strong>110</strong> products
first promoted in 2025–2026, only <strong>24</strong> publish inventory yet. Median
<strong>850 codes</strong>, median entry price <strong>$59</strong>, median satisfaction
<strong>91.0%</strong>. The strongest recent paid launches are ProxiedMail (2,838 codes at a
<strong>$10</strong> entry, 91.0%), Deftform (2,265 at $49, <strong>96.0%</strong>) and Bit Form
(2,200 at $79, 92.4%) — all narrow-utility tools in Forms, Email and Productivity, not
platform plays. Note that <strong>20 of the 110</strong> already have a claim contradicted by their
own buyers: the promise problem starts on day one, not after scale.</p>

<p><strong>The synthesis.</strong> A launch here is a 3.5-year commitment sold per licence code at a
$59 median entry, on a uniform 60/60-day contract, into a calendar of near-universal seasonal sales
where the scarce signal is a DOTD slot. Promotion buys exposure and erodes satisfaction but does not
reliably buy volume. The winners are narrow, cheap, verifiable-in-one-session utilities that keep
their promise — and the ones that get discounted consistently enough that nobody feels they
overpaid.</p>
"""
