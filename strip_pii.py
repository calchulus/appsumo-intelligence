"""Strip reviewer identifiers from the raw crawl JSONL files, in place.

Removes the structured `user_name` field (full_name / username / email, whichever AppSumo
returned) from every comment record and any nested replies. Review text, star rating and
helpful-vote counts are preserved.

Also scans the surviving review text for residual identifiers (email addresses) so we know
what free-text PII remains, since that cannot be scrubbed mechanically without damaging
the quotes.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Every file that can carry reviewer identity or an email address. pages.jsonl was the big
# one: it stores the product page's review/question samples, which include `user_name`
# (12,976 occurrences) and 158 emails. promise.jsonl carries vendor contact addresses from
# listing copy and FAQs. analysis.json / index.html inherit both, so the whole downstream
# pipeline must be re-run after scrubbing.
FILES = ["reviews.jsonl", "positive.jsonl", "pages.jsonl", "promise.jsonl"]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
IDENT_KEYS = {"user_name", "user", "full_name", "username", "email", "author",
              "user_email", "first_name", "last_name", "avatar", "avatar_url"}


def scrub(node, stats):
    if isinstance(node, dict):
        for k in list(node.keys()):
            if k in IDENT_KEYS:
                node.pop(k)
                stats["fields_removed"] += 1
            else:
                scrub(node[k], stats)
    elif isinstance(node, list):
        for x in node:
            scrub(x, stats)


def text_of(node, out):
    if isinstance(node, dict):
        for k in ("comment", "title"):
            v = node.get(k)
            if isinstance(v, str):
                out.append(v)
        for v in node.values():
            text_of(v, out)
    elif isinstance(node, list):
        for x in node:
            text_of(x, out)


def redact_emails(node, stats):
    """Redact emails in EVERY string field, not just review text. promise.jsonl carries
    vendor contact addresses inside listing copy and FAQ answers, and pages.jsonl carries
    them inside review samples -- restricting to ("comment","title") missed both."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                new = EMAIL.sub("[email redacted]", v)
                if new != v:
                    stats["emails_redacted"] += len(EMAIL.findall(v))
                    node[k] = new
            else:
                redact_emails(v, stats)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            if isinstance(x, str):
                new = EMAIL.sub("[email redacted]", x)
                if new != x:
                    stats["emails_redacted"] += len(EMAIL.findall(x))
                    node[i] = new
            else:
                redact_emails(x, stats)


for fn in FILES:
    path = os.path.join(HERE, fn)
    if not os.path.exists(path):
        print(f"skip (missing): {fn}", file=sys.stderr)
        continue
    recs, stats, texts = [], {"fields_removed": 0, "emails_redacted": 0}, []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        scrub(r, stats)
        redact_emails(r, stats)
        text_of(r, texts)
        recs.append(r)
    blob = "\n".join(texts)
    emails = sorted(set(EMAIL.findall(blob)))
    before = os.path.getsize(path)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    print(f"{fn}: {len(recs)} records, {stats['fields_removed']} identity fields removed, "
          f"{stats['emails_redacted']} emails redacted, "
          f"{before/1e6:.1f}MB -> {os.path.getsize(path)/1e6:.1f}MB", file=sys.stderr)
    print(f"   residual email-like strings in review text: {len(emails)}", file=sys.stderr)
    for e in emails[:10]:
        print(f"     {e}", file=sys.stderr)

# verify nothing survived
leftover = 0
for fn in FILES:
    path = os.path.join(HERE, fn)
    if not os.path.exists(path):
        continue
    s = open(path).read()
    for k in ("user_name", '"username"', '"full_name"', '"email"'):
        leftover += s.count(k)
print(f"\nVERIFICATION: identity keys remaining across both files = {leftover}", file=sys.stderr)
sys.exit(1 if leftover else 0)
