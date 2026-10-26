#!/usr/bin/env python3
"""Render the Campaign Highlights section HTML from campaign_highlights.json.

Kept separate from build_dashboard.py so the campaign economics can be re-derived and re-rendered
without touching the 1,100-line builder. build_dashboard.py imports `render()`.

Design rules this follows:
  * Paid lifetime codes and free downloads are NEVER blended into one ranking.
  * Revenue is labelled gross, with the floor-ceiling range shown, and the vendor-net gap stated.
  * Every table row links to the live listing so a reader can check it.
  * Campaign age is shown next to every velocity figure - $/day without duration is meaningless when
    the median listing has been live 3.5 years.
"""
import html as _h
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return _h.escape(str(s if s is not None else ""))


def money(v, dp=0):
    if v is None:
        return "&mdash;"
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.0f}k" if dp == 0 else f"${v/1_000:.1f}k"
    return f"${v:,.0f}"


def num(v):
    return "&mdash;" if v is None else f"{int(v):,}"


def years(days):
    if not days:
        return "&mdash;"
    return f"{days/365.25:.1f}y" if days >= 365 else f"{days}d"


def _row(c, rank, show_rev=True):
    name = esc(c["name"])
    url = c.get("url") or ""
    link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{name}</a>' if url else name
    rev = (f'<td class="num"><strong>{money(c["rev_point"])}</strong>'
           + (f'<div class="mut">{money(c["rev_floor"])}&ndash;{money(c["rev_ceiling"])}</div>'
              if c["rev_ceiling"] and c["rev_ceiling"] != c["rev_floor"] else "")
           + "</td>") if show_rev else ""
    stars = f'{c["rating"]:.1f}&#9733; <span class="mut">({num(c["review_count"])})</span>' \
        if c.get("rating") else "&mdash;"
    lad = {"linear": "linear", "progressive": "rising/code", "single-tier": "1 tier"}.get(
        c.get("ladder_shape"), c.get("ladder_shape") or "&mdash;")
    return (f'<tr><td class="r mut">{rank}</td><td>{link}'
            f'<div class="mut">{esc(c.get("category") or "")} &middot; {esc(c.get("listing") or "")}</div></td>'
            f'<td class="num">{num(c["units"])}</td>'
            f'<td class="num">${c["entry_price"] or 0:,.0f}</td>'
            f'{rev}'
            f'<td class="num">{money(c.get("rev_per_day")) if show_rev else "&mdash;"}'
            f'<div class="mut">{years(c.get("days_live"))} live</div></td>'
            f'<td class="num">{esc(c.get("tier_count") or "")}<div class="mut">{esc(lad)}</div></td>'
            f'<td class="num">{esc(c.get("max_codes_per_purchase") or 1)}</td>'
            f'<td class="num">{esc(c.get("refundable_days"))}d</td>'
            f'<td class="num">{stars}</td></tr>')


HEAD = ("<thead><tr><th class='num'>#</th><th>Campaign</th><th class='num'>Lifetime codes</th>"
        "<th class='num'>Entry</th>"
        "<th class='num'>Gross revenue<div class='mut'>floor&ndash;ceiling</div></th>"
        "<th class='num'>$ / day<div class='mut'>age</div></th>"
        "<th class='num'>Tiers<div class='mut'>ladder</div></th>"
        "<th class='num'>Codes<br>per buy</th><th class='num'>Refund</th>"
        "<th class='num'>Rating</th></tr></thead>")


def render(path=None):
    d = json.load(open(path or os.path.join(HERE, "campaign_highlights.json"), encoding="utf-8"))
    a, t, m = d["aggregate"], d["terms"], d["method"]
    o = []
    w = o.append

    w('<div class="card">')
    w('<h2>What the best campaigns actually sold</h2>')
    w('<p class="sub">Lifetime codes sold, gross revenue, campaign age and the contractual terms, '
      'for every AppSumo listing that publishes inventory. Snapshot ' + esc(a["snapshot"]) + '.</p>')

    w('<div class="chips">')
    for label, val, sub in [
        ("Campaigns measured", num(a["campaigns_with_units"]),
         f'{a["paid_campaigns"]} paid &middot; {a["freebie_campaigns"]} free'),
        ("Lifetime codes sold", num(a["total_units_paid"]), "paid campaigns only"),
        ("Gross revenue", money(a["gross_rev_point"]),
         f'range {money(a["gross_rev_floor"])}&ndash;{money(a["gross_rev_ceiling"])}'),
        ("Median campaign age", years(a["median_days_live"]),
         f'{a["still_live"]} still live'),
    ]:
        w(f'<div class="chip"><b>{val}</b><span>{label}</span>'
          f'<div class="mut">{sub}</div></div>')
    w('</div>')

    w('<div class="note"><strong>Read this before using any number below.</strong><br>'
      '<b>Gross, not net.</b> This is what buyers paid AppSumo. AppSumo&rsquo;s revenue split with '
      'vendors is not in this dataset and is not published per deal, so <b>vendor take-home is not '
      'derivable here</b> &mdash; nothing below is profit.<br>'
      '<b>Codes, not purchases.</b> ' + esc(m["units"].split("Counts")[-1].strip(" .-")) +
      ' A tier-5 purchase granting 5 codes counts as 5. For <b>linear</b> ladders price-per-code is '
      'constant, so revenue is unaffected; for <b>rising</b> ladders the floor understates.<br>'
      '<b>Coverage is partial.</b> ' + esc(m["coverage"]) + '<br>'
      '<b>Age, not launch window.</b> ' + esc(m["duration"]) + '</div>')
    w('</div>')

    # ---------------- top by revenue ----------------
    w('<div class="card"><h2>Highest-grossing campaigns</h2>')
    w('<p class="sub">Ranked by gross revenue (point estimate). The floor&ndash;ceiling spread is '
      'shown only where it is non-zero; for ' + str(a["linear_campaigns"]) + ' linear ladders '
      'price-per-code is constant and the figure is exact.</p>')
    w('<div class="tblwrap"><table>' + HEAD + '<tbody>')
    for i, c in enumerate(d["top_by_revenue"][:20], 1):
        w(_row(c, i))
    w('</tbody></table></div>')
    top5 = sum(c["rev_point"] for c in d["top_by_revenue"][:5])
    tot = a["gross_rev_point"] or 1
    w(f'<p class="mut">Top 5 campaigns = <strong>{money(top5)}</strong>, i.e. '
      f'<strong>{top5*100/tot:.0f}%</strong> of all measured gross revenue. '
      f'Top 20 = {sum(c["rev_point"] for c in d["top_by_revenue"][:20])*100/tot:.0f}%.</p>')
    w('</div>')

    # ---------------- velocity ----------------
    w('<div class="card"><h2>Fastest earners &mdash; revenue per day live</h2>')
    w('<p class="sub">A different question from total revenue. Because the median listing has been '
      'live ' + years(a["median_days_live"]) + ', total revenue favours old listings; $/day shows '
      'which campaigns are actually pulling. <strong>Read the age column</strong> &mdash; a high '
      'rate over 19 days is a launch, over 1,900 days is an evergreen annuity.</p>')
    w('<div class="tblwrap"><table>' + HEAD + '<tbody>')
    for i, c in enumerate(d["top_by_velocity"][:15], 1):
        w(_row(c, i))
    w('</tbody></table></div>')
    young = [c for c in d["top_by_velocity"][:15] if (c.get("days_live") or 0) <= 120]
    if young:
        w('<p class="mut">Of the top 15 by velocity, <strong>' + str(len(young)) +
          '</strong> have been live 120 days or less &mdash; these are the genuine launch '
          'performances: ' + ', '.join(f'{esc(c["name"])} ({money(c["rev_per_day"])}/day over '
                                      f'{c["days_live"]}d)' for c in young[:4]) + '.</p>')
    w('</div>')

    # ---------------- volume ----------------
    w('<div class="card"><h2>Most lifetime codes sold</h2>')
    w('<p class="sub">Volume, independent of price. Cheap high-volume campaigns and expensive '
      'low-volume ones rank very differently here than by revenue.</p>')
    w('<div class="tblwrap"><table>' + HEAD + '<tbody>')
    for i, c in enumerate(d["top_by_units"][:15], 1):
        w(_row(c, i))
    w('</tbody></table></div></div>')

    # ---------------- freebies ----------------
    w('<div class="card"><h2>Free lead magnets &mdash; kept separate on purpose</h2>')
    w(f'<p class="sub">{a["freebie_campaigns"]} freebie campaigns moved '
      f'<strong>{num(a["total_units_free"])}</strong> downloads, '
      f'{a["freebies_at_zero"]} of them at exactly $0. These are distribution, not revenue, and '
      f'blending them into a sales ranking is how the single biggest "seller" on the site turns out '
      f'to be a free Google Sheets template.</p>')
    w('<div class="tblwrap"><table><thead><tr><th class="num">#</th><th>Campaign</th>'
      '<th class="num">Downloads</th><th class="num">Price</th><th class="num">Age</th>'
      '<th class="num">Rating</th></tr></thead><tbody>')
    for i, c in enumerate(d["top_freebies"], 1):
        nm = esc(c["name"])
        u = c.get("url") or ""
        link = f'<a href="{esc(u)}" target="_blank" rel="noopener">{nm}</a>' if u else nm
        st = f'{c["rating"]:.1f}&#9733; <span class="mut">({num(c["review_count"])})</span>' \
            if c.get("rating") else "&mdash;"
        w(f'<tr><td class="r mut">{i}</td><td>{link}'
          f'<div class="mut">{esc(c.get("category") or "")}</div></td>'
          f'<td class="num">{num(c["units"])}</td>'
          f'<td class="num">{"free" if not c["rev_point"] else money(c["entry_price"])}</td>'
          f'<td class="num">{years(c.get("days_live"))}</td><td class="num">{st}</td></tr>')
    w('</tbody></table></div></div>')

    # ---------------- terms ----------------
    cp = t["clause_prevalence"]
    n = t["measured_over"]
    w('<div class="card"><h2>The terms these campaigns ran on</h2>')
    w(f'<p class="sub">Measured across all {n} live products, not just those publishing inventory, '
      f'so the sample is not biased toward code-fulfilled deals.</p>')
    w('<div class="chips">')
    ref = t["refund_window_days"]
    w(f'<div class="chip"><b>{ref.get("60",0)}/{n}</b><span>60-day refund window</span>'
      f'<div class="mut">{ref.get("0",0)} offer none &middot; '
      f'{ref.get("365",0)} a full year</div></div>')
    w(f'<div class="chip"><b>{t["redemption_window_days"].get("60",0)}/{n}</b>'
      f'<span>60-day code redemption</span><div class="mut">use it or lose it</div></div>')
    w(f'<div class="chip"><b>{cp.get("stacking_mentioned",0)}</b><span>mention stacking</span>'
      f'<div class="mut">buy multiple codes to scale</div></div>')
    w(f'<div class="chip"><b>{cp.get("new_users_only",0)}</b><span>new customers only</span>'
      f'<div class="mut">no existing accounts or trials</div></div>')
    w('</div>')
    w(f'<p><strong>The contract is remarkably uniform.</strong> '
      f'{ref.get("60",0)} of {n} listings carry the same 60-day refund window, and '
      f'{t["redemption_window_days"].get("60",0)} impose a 60-day code-redemption deadline &mdash; '
      f'the two windows are the same length, so the refund right and the activation deadline expire '
      f'together. {cp.get("plan_name_transfers",0)} listings promise the licence follows the product '
      f'if the vendor renames the plan, which is the clause that makes a lifetime deal survivable '
      f'across a rebrand. Only {cp.get("new_users_only",0)} explicitly exclude existing customers.</p>')
    w('<div class="tblwrap"><table><thead><tr>'
      '<th>Ladder shape (price-based vs price-per-code)</th><th class="num">Products</th>'
      '<th>What it means for revenue</th></tr></thead><tbody>')
    EXPL = {
        "linear": "price scales exactly with codes &rarr; revenue per code is constant, so "
                  "codes &times; entry price is exact",
        "progressive": "price per code rises with tier &rarr; the entry-price floor understates; "
                       "the ceiling column bounds it",
        "single-tier": "one price point &rarr; no ambiguity",
        "none": "ladder not published",
    }
    for k, v in t["ladder_shape_crosstab"].items():
        parts = dict(kv.split("=") for kv in k.split(" / "))
        pc = parts.get("per-code-shape", "")
        w(f'<tr><td>{esc(k)}</td><td class="num">{v}</td><td class="mut">{EXPL.get(pc,"")}</td></tr>')
    w('</tbody></table></div>')
    w(f'<p class="mut"><strong>{a["multi_code_tiers"]}</strong> of the {a["paid_campaigns"]} paid '
      f'campaigns sell tiers that grant more than one code per purchase &mdash; that is why units '
      f'are codes and not orders.</p>')
    w('</div>')

    return "\n".join(o)


if __name__ == "__main__":
    h = render()
    print(f"rendered {len(h)/1024:.1f} KB of section HTML")
    open(os.path.join(HERE, "_campaigns_preview.html"), "w", encoding="utf-8").write(h)
    print("wrote _campaigns_preview.html")
