"""Render-test the dashboard headless via file:// and assert on observable output.

ASSERTIONS ARE SPLIT INTO MANY SMALL Runtime.evaluate CALLS. A single monolithic
~200-line script returns `null` and kills the CDP socket on this page size (4 MB,
342 rendered cards) -- the same failure mode recorded for the Nanshan render test.
Each group below is one evaluate; `ok()` accumulates into window.__R.

os._exit(0) is the LAST statement inside main(): asyncio.run() hangs during loop
shutdown (browser-use's CDP websocket reconnect loop), so an outer finally never runs.
"""
import asyncio, json, os, sys

from browser_use import BrowserSession, BrowserProfile

HERE = "/Users/calvinchu/appsumo_products"
FRAG = os.path.join(HERE, "appsumo_dashboard.html")
TEST = os.path.join(HERE, "_test_wrap.html")

# Test index.html directly when present: that is the exact file GitHub Pages serves, so it
# is the thing worth verifying. Fall back to wrapping the body-only artifact fragment.
PAGES = os.path.join(HERE, "index.html")
if os.path.exists(PAGES):
    URL = "file://" + PAGES
    TARGET = "index.html (the deployed file)"
else:
    frag = open(FRAG).read()
    open(TEST, "w").write("<!doctype html><html><head><meta charset='utf-8'>"
                          "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                          "<title>t</title></head><body>" + frag + "</body></html>")
    URL = "file://" + TEST
    TARGET = "_test_wrap.html (wrapped fragment)"
print("testing:", TARGET, flush=True)

BOOT = r"""
window.__errs = [];
window.__R = [];
window.addEventListener('error', e => __errs.push(String(e.message)));
window.addEventListener('unhandledrejection', e => __errs.push('rej:' + String(e.reason)));
window.ok = (name, cond, extra) => __R.push(
  {name: name, pass: !!cond, extra: extra == null ? null : String(extra)});
window.$ = s => document.querySelector(s);
window.$$ = s => [...document.querySelectorAll(s)];
"""

STEPS = [
("errors + summary tab", r"""
(()=>{ ok('no JS errors', __errs.length===0, JSON.stringify(__errs.slice(0,5)));
 ok('7 tabs', $$('nav button').length===7, $$('nav button').length);
 ok('Summary is default tab', !$('#summary').hidden && $('#insights').hidden, '');
 ok('9 key takeaways', $$('#keyTakeaways .tk').length===9, $$('#keyTakeaways .tk').length);
 ok('takeaways numbered 1..9',
    $$('#keyTakeaways .tkn').map(e=>e.textContent).join(',')==='1,2,3,4,5,6,7,8,9', '');
 ok('each takeaway cites evidence', $$('#keyTakeaways .ev').length===9, $$('#keyTakeaways .ev').length);
 ok('glance table 18 rows', $$('#glanceTable tbody tr').length===18, $$('#glanceTable tbody tr').length);
 ok('glance table labels codes not units',
    ($('#glanceTable').textContent||'').includes('License codes issued')
    && !($('#glanceTable').textContent||'').includes('Derived paid units sold'), '');
 // sold_estimate counts LICENSE CODES, and ~125k of them are $0 lead magnets, so the
 // headline must be the paid figure (497,195) not the raw total (622,571).
 ok('headline cites PAID codes', $('#sUnits').textContent==='497,195 paid', $('#sUnits').textContent);
 ok('product count filled', $('#sProds').textContent==='342', $('#sProds').textContent);
 ok('total codes + campaign count filled',
    $('#sUnitsAll').textContent==='622,571' && $('#sCamp').textContent==='75',
    $('#sUnitsAll').textContent+'/'+$('#sCamp').textContent);
 ok('review-text count = 8208', parseInt($('#sRevText').textContent.replace(/,/g,''))===8208,
    $('#sRevText').textContent);
 ok('so-what rendered', ($('#soWhat').textContent||'').length>600, ($('#soWhat').textContent||'').length);
 ok('confidence box rendered', ($('#confBox').textContent||'').includes('0.3% median error'), '');
  return 'ok';})()
"""),
("insights tab", r"""
(()=>{ $$('nav button')[1].click();
 ok('Insights visible', !$('#insights').hidden && $('#summary').hidden, '');
 ok('13 painpoint bars', $$('#painChart .barrow').length===13, $$('#painChart .barrow').length);
 ok('8 question bars', $$('#qChart .barrow').length===8, $$('#qChart .barrow').length);
 ok('sold table 25 rows', $$('#soldTable tbody tr').length===25, $$('#soldTable tbody tr').length);
 ok('downloads table 10 rows', $$('#dlTable tbody tr').length===10, $$('#dlTable tbody tr').length);
 ok('category table rows', $$('#catTable tbody tr').length>20, $$('#catTable tbody tr').length);
 ok('synth prose rendered', ($('#synth').textContent||'').length>1500, ($('#synth').textContent||'').length);
  return 'ok';})()
"""),
("painpoint drill-down", r"""
(()=>{ const b=$('#painChart button.barwrap'); b.click();
 const q=$('#painChart').parentElement.querySelector('.qbox');
 ok('pain bar click reveals quotes', !!q && q.querySelectorAll('.q').length>0, q?q.querySelectorAll('.q').length:'none');
 ok('quote shows trigger token', q ? q.textContent.includes('matched') : false, '');
 b.click();
 ok('pain quote box collapses', !$('#painChart').parentElement.querySelector('.qbox'), '');
  return 'ok';})()
"""),
("promise tab", r"""
(()=>{ $$('nav button')[2].click();
 ok('Promise visible', !$('#promise').hidden && $('#insights').hidden, '');
 ok('13 praise bars', $$('#posChart .barrow').length===13, $$('#posChart .barrow').length);
 ok('5 satisfaction bands', $$('#satChart .barrow').length===5, $$('#satChart .barrow').length);
 ok('sat bands sum to 250',
    $$('#satChart .barval').map(e=>parseInt(e.textContent)).reduce((a,b)=>a+b,0)===250,
    $$('#satChart .barval').map(e=>e.textContent).join('|'));
 const g=$('#gapBox').textContent||'';
 ok('gap box cites 165 of 250', g.includes('165')&&g.includes('250'), g.slice(0,80));
 ok('gap box cites 42% median', g.includes('42%'), '');
 ok('best table populated', $$('#bestTable tbody tr').length>=8, $$('#bestTable tbody tr').length);
 ok('fail table populated', $$('#failTable tbody tr').length>=8, $$('#failTable tbody tr').length);
 ok('synth2 rendered', ($('#synth2').textContent||'').length>2500, ($('#synth2').textContent||'').length);
  return 'ok';})()
"""),
("praise drill-down", r"""
(()=>{ const b=$('#posChart button.barwrap'); b.click();
 const q=$('#posChart').parentElement.querySelector('.qbox');
 ok('praise bar click reveals quotes', !!q && q.querySelectorAll('.q').length>0, q?q.querySelectorAll('.q').length:'none');
 b.click();
 ok('praise quote box collapses', !$('#posChart').parentElement.querySelector('.qbox'), '');
  return 'ok';})()
"""),
("claims tab", r"""
(()=>{ $$('nav button')[3].click();
 ok('Claims visible', !$('#claims').hidden && $('#promise').hidden, '');
 ok('14 archetypes charted', $$('#archChart .barrow').length===14, $$('#archChart .barrow').length);
 ok('archetype bars show rate+counts', /% · \d+\/\d+/.test($('#archChart .barval').textContent),
    $('#archChart .barval').textContent);
 ok('xref counts filled', $('#xrN').textContent==='101' && $('#xrR').textContent==='310'
    && $('#xrM').textContent==='27',
    [$('#xrN').textContent,$('#xrR').textContent,$('#xrM').textContent].join('/'));
 ok('101 products listed', $$('#xList .xr').length===101, $$('#xList .xr').length);
 ok('xCount matches', ($('#xCount').textContent||'').startsWith('101'), $('#xCount').textContent);
 ok('synth3 rendered', ($('#synth3').textContent||'').length>2500, ($('#synth3').textContent||'').length);
  return 'ok';})()
"""),
("claims filter + sort", r"""
(()=>{ const xa=$('#xArch'), xs=$('#xSort');
 ok('archetype filter has 15 options', xa.options.length===15, xa.options.length);
 xa.value='ease'; xa.dispatchEvent(new Event('change',{bubbles:true}));
 ok('filter ease -> 50 products', $$('#xList .xr').length===50, $$('#xList .xr').length);
 ok('every filtered card carries the claim',
    $$('#xList .xr').every(e=>e.textContent.includes('Easy / simple')), '');
 xa.value=''; xa.dispatchEvent(new Event('change',{bubbles:true}));
 ok('filter reset restores 101', $$('#xList .xr').length===101, $$('#xList .xr').length);
 xs.value='n'; xs.dispatchEvent(new Event('change',{bubbles:true}));
 const top=$('#xList .xr .pname').textContent.trim();
 ok('sort by claims -> BreezeDoc first', /BreezeDoc/.test(top), top.slice(0,50));
 xs.value='sat'; xs.dispatchEvent(new Event('change',{bubbles:true}));
 ok('sort by satisfaction reorders', $('#xList .xr .pname').textContent.trim()!==top, '');
 xs.value='n'; xs.dispatchEvent(new Event('change',{bubbles:true}));
  return 'ok';})()
"""),
("claims card expansion", r"""
(()=>{ const d=$('#xList .xr'); d.open=true; d.dispatchEvent(new Event('toggle',{bubbles:true}));
 const b=d.querySelector('.xrb'); const t=b?b.textContent:'';
 ok('xref card expands with pairs', !!b && b.querySelectorAll('.pair').length>=3,
    b?b.querySelectorAll('.pair').length:0);
 ok('pair shows promised text', t.includes('Promised:'), '');
 ok('pair shows star + helpful votes', /\d★ · \d+ found helpful/.test(t), '');
 ok('pair shows trigger token', t.includes('trigger'), '');
 ok('pair links to listing', b.querySelectorAll('a[href*="appsumo.com"]').length>0,
    b?b.querySelectorAll('a').length:0);
  return 'ok';})()
"""),
("archetype drill-down", r"""
(()=>{ const b=$('#archChart button.barwrap'); b.click();
 const q=$('#archChart').parentElement.querySelector('.qbox');
 ok('archetype bar reveals pairs', !!q && q.querySelectorAll('.pair').length>0,
    q?q.querySelectorAll('.pair').length:'none');
 b.click();
 ok('archetype drill-down collapses', !$('#archChart').parentElement.querySelector('.qbox'), '');
  return 'ok';})()
"""),
("campaigns tab", r"""
(()=>{ $$('nav button')[4].click();
 ok('Campaigns visible', !$('#campaigns').hidden && $('#claims').hidden, '');
 const b=$('#campBody');
 ok('campaigns body injected', !!b && b.children.length>=6, b?b.children.length:0);
 const txt=b.innerText||'';
 ok('states gross revenue', /\$30\.\d\dM/.test(txt), (txt.match(/\$30\.\d\dM/)||[])[0]);
 ok('states codes sold', /497,195/.test(txt), '');
 ok('names the top campaign', /WordHero/.test(txt), '');
 ok('gross-not-net caveat present', /vendor take-home is not derivable/i.test(txt), '');
 ok('codes-not-purchases caveat present', /Codes, not purchases/i.test(txt), '');
 ok('coverage caveat present', /133 publish nothing|excluded rather than proxied/i.test(txt), '');
 ok('has revenue table rows', b.querySelectorAll('table tbody tr').length>=40,
    b.querySelectorAll('table tbody tr').length);
 ok('refund terms shown', /60-day refund window/i.test(txt), '');
 // .chip span is text-transform:uppercase, so innerText is upper-cased - match case-insensitively
 // and accept either the chip wording or the hyphenated prose form.
 ok('redemption terms shown', /60-day code[- ]redemption/i.test(txt), '');
 ok('redemption count rendered', /297\/342/.test(txt.replace(/\s+/g,'')), '');
 ok('freebies kept separate', /Free lead magnets/.test(txt), '');
 ok('velocity section present', /revenue per day live/i.test(txt), '');
 ok('ladder crosstab present', /per-code-shape/.test(txt), '');
 ok('no unrendered None', !/>\s*None\s*</.test(b.innerHTML), '');
 ok('no NaN in tables', !/NaN/.test(txt), '');
 return 'ok';})()
"""),
("browse tab + search", r"""
(()=>{ $$('nav button')[5].click();
 ok('Browse visible', !$('#browse').hidden && $('#campaigns').hidden, '');
 ok('342 cards rendered', $$('#list .prod').length===342, $$('#list .prod').length);
 ok('count label 342 of 342', ($('#count').textContent||'').startsWith('342 of 342'), $('#count').textContent);
 const q=$('#q'); q.value='zapier'; q.dispatchEvent(new Event('input',{bubbles:true}));
 ok('search narrows', !($('#count').textContent||'').startsWith('342'), $('#count').textContent);
 q.value='refund'; q.dispatchEvent(new Event('input',{bubbles:true}));
 const n=parseInt(($('#count').textContent||'0'),10);
 ok('search matches painpoint theme text', n>5&&n<342, n);
 q.value=''; q.dispatchEvent(new Event('input',{bubbles:true}));
 ok('search reset restores 342', ($('#count').textContent||'').startsWith('342 of 342'), $('#count').textContent);
  return 'ok';})()
"""),
("browse filters + sorts", r"""
(()=>{ const g=$('#fGroup'), s=$('#fSort');
 ok('Operations option exists', !![...g.options].find(o=>o.value==='Operations'), '');
 g.value='Operations'; g.dispatchEvent(new Event('change',{bubbles:true}));
 ok('group filter -> 102', parseInt(($('#count').textContent||'0'),10)===102, $('#count').textContent);
 ok('category select repopulated', $('#fCat').options.length>3, $('#fCat').options.length);
 g.value=''; g.dispatchEvent(new Event('change',{bubbles:true}));
 s.value='sold'; s.dispatchEvent(new Event('change',{bubbles:true}));
 const a=$('#list .prod .pname').textContent.trim();
 ok('units-sold sort leads with a paid seller', /ApproveMe|Intellifluence|Switchy/.test(a), a.slice(0,50));
 s.value='dl'; s.dispatchEvent(new Event('change',{bubbles:true}));
 ok('downloads sort leads with a freebie',
    /Google Sheets Template Pack|Million Dollar Email/.test($('#list .prod .pname').textContent), '');
 s.value='rating'; s.dispatchEvent(new Event('change',{bubbles:true}));
 ok('rating sort reorders', $('#list .prod .pname').textContent.trim()!==a, '');
 s.value='claims'; s.dispatchEvent(new Event('change',{bubbles:true}));
 ok('claims sort works', $$('#list .prod').length===342, $$('#list .prod').length);
  return 'ok';})()
"""),
("browse card expansion", r"""
(()=>{ const s=$('#fSort'); s.value='claims'; s.dispatchEvent(new Event('change',{bubbles:true}));
 const d=$('#list .prod'); d.open=true; d.dispatchEvent(new Event('toggle',{bubbles:true}));
 const b=d.querySelector('.pbody'); const t=b?b.textContent:'';
 ok('card body rendered', !!b && t.length>300, b?t.length:0);
 ok('shows vendor promise', t.includes('What it purports to serve'), '');
 ok('shows promise-vs-delivery verdict', t.includes('Promise vs delivery'), '');
 ok('shows exact satisfaction rate', /% of [\d,]+ reviews are 4–5★/.test(t), '');
 ok('shows star split', t.includes('star split'), '');
 ok('shows contradicted-claims panel', t.includes('Claims contradicted by buyers'), '');
 ok('claims panel has pairs + triggers', b.querySelectorAll('.pair').length>0 && t.includes('trigger'),
    b.querySelectorAll('.pair').length);
 ok('claims pill severity rendered', !!b.querySelector('.pill.hi,.pill.md,.pill.lo'), '');
 ok('shows praise themes', t.includes('Praise themes'), '');
 ok('shows happy-buyer quotes', t.includes('What happy buyers said'), '');
 ok('shows painpoint tags', b.querySelectorAll('.tag.r').length>0, b.querySelectorAll('.tag.r').length);
 ok('shows links', b.querySelectorAll('a').length>=1, b.querySelectorAll('a').length);
 s.value='sold'; s.dispatchEvent(new Event('change',{bubbles:true}));
  return 'ok';})()
"""),
("method tab + leak scan", r"""
(()=>{ $$('nav button')[6].click();
 ok('Method visible', !$('#method').hidden && $('#browse').hidden, '');
 ok('method lists 10 passes', $$('#srcTable tbody tr').length===10, $$('#srcTable tbody tr').length);
 const c=$('#cavBox').textContent||'';
 ok('caveat 4b present', c.includes('Positive review TEXT is a 26% sample'), '');
 ok('caveat 5b present', c.includes('Contradiction rates are floors'), '');
 ok('coverage box present', ($('#covBox').textContent||'').includes('342/342'), '');
 $$('nav button')[0].click();
 ok('back to Summary', !$('#summary').hidden && $('#method').hidden, '');
 // template-leak scan. Customer text legitimately contains "undefined" (pasted JS errors),
 // so check the shapes a real template bug produces rather than the bare word.
 const clone=document.body.cloneNode(true);
 clone.querySelectorAll('.q,.note,.cm,.cl,#cavBox,#covBox,#synth,#synth2,#synth3').forEach(e=>e.remove());
 const st=clone.textContent;
 const LEAK=[/>undefined</,/\bundefined%/,/\$undefined/,/\bNaN\b/,/\[object Object\]/,/>\s*undefined\s*</];
 const hit=LEAK.find(rx=>rx.test(st));
 ok('no template leaks', !hit, hit?String(hit):'');
  return 'ok';})()
"""),
]


async def ev(session, cdp, expr):
    r = await session.cdp_client.send.Runtime.evaluate(
        params={"expression": expr, "returnByValue": True}, session_id=cdp.session_id)
    return (getattr(r.result, "value", None) if hasattr(r, "result")
            else r.get("result", {}).get("value"))


async def main():
    session = BrowserSession(browser_profile=BrowserProfile(headless=True, enable_default_extensions=False))
    await session.start()
    await asyncio.wait_for(session.new_page("about:blank"), timeout=70)
    tgt = next((t for t in session.get_page_targets() if "about:blank" in (t.url or "")),
               session.get_page_targets()[0])
    cdp = await session.get_or_create_cdp_session(target_id=tgt.target_id)
    await session.cdp_client.send.Page.addScriptToEvaluateOnNewDocument(
        params={"source": BOOT}, session_id=cdp.session_id)
    await session.cdp_client.send.Page.navigate(params={"url": URL}, session_id=cdp.session_id)
    await asyncio.sleep(30)

    ncards = await ev(session, cdp, "document.querySelectorAll('#list .prod').length")
    print(f"cards_on_load={ncards}", flush=True)

    for label, js in STEPS:
        try:
            r = await asyncio.wait_for(ev(session, cdp, js), timeout=60)
            if r is None:
                print(f"  !! evaluate returned null for group: {label}", flush=True)
        except Exception as e:
            print(f"  !! group '{label}' failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        print(f"  [done] {label}", flush=True)

    raw = await ev(session, cdp, "JSON.stringify(window.__R)")
    try:
        res = json.loads(raw)
    except Exception:
        print("COULD NOT READ RESULTS:", str(raw)[:400], flush=True)
        sys.stdout.flush(); os._exit(2)
    for r in res:
        mark = "PASS" if r["pass"] else "FAIL"
        ex = f"  [{r['extra']}]" if r.get("extra") not in (None, "") else ""
        print(f"  {mark}  {r['name']}{ex}", flush=True)
    print(f"\nRESULT assertions={len(res)} failed={sum(1 for r in res if not r['pass'])}", flush=True)
    sys.stdout.flush()
    os._exit(0)


try:
    asyncio.run(asyncio.wait_for(main(), 290))
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:500], flush=True)
finally:
    sys.stdout.flush()
    os._exit(1)
