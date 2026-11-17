"""Compare a translated copy of a page with its source. Each check returns one result row."""
import re

from . import lang as langmod

PASS, WARN, FAIL, INFO = "pass", "warn", "fail", "info"


def _row(check, status, summary, details=None):
    return {"check": check, "status": status, "summary": summary, "details": details or []}


def _page_lang(page):
    text = " ".join(x for _, x in page["blocks"])
    return langmod.guess(text, min_hits=5) or page["lang"]


def check_language(src, copy, target):
    declared = copy["lang"]
    if declared is None:
        return _row("language tag", WARN, "The copy has no lang attribute on <html>.")
    if declared != target:
        return _row("language tag", WARN, "The copy declares lang=\"%s\", expected \"%s\"." % (declared, target))
    return _row("language tag", PASS, "The copy declares lang=\"%s\"." % declared)


def check_leftovers(src, copy, target, source_lang, ignore):
    hits = []
    for tag, text in copy["blocks"]:
        if any(i.lower() in text.lower() for i in ignore):
            continue
        sc = langmod.scores(text)
        if sc.get(source_lang, 0) >= 2 and sc[source_lang] > sc.get(target, 0):
            hits.append("<%s> %s" % (tag, text[:140]))
    if hits:
        return _row("leftover source text", FAIL,
                    "%d text block(s) still read as %s." % (len(hits), source_lang), hits)
    return _row("leftover source text", PASS, "No text block reads as %s." % source_lang)


def check_identical(src, copy, ignore):
    """Short strings copied letter for letter: often an untranslated button or label."""
    src_texts = {x.lower() for _, x in src["blocks"]}
    same = []
    for tag, text in copy["blocks"]:
        letters = re.sub(r"[\W\d_]+", "", text)
        if len(letters) < 4 or len(text) > 60:
            continue
        if any(i.lower() in text.lower() for i in ignore):
            continue
        if text.lower() in src_texts:
            same.append("<%s> %s" % (tag, text))
    same = sorted(set(same))
    if same:
        return _row("identical short strings", WARN,
                    "%d short string(s) are identical to the source. Names are fine; labels are not." % len(same), same)
    return _row("identical short strings", PASS, "No short string is copied unchanged.")


def check_structure(src, copy):
    s = [t for t, _ in src["headings"]]
    c = [t for t, _ in copy["headings"]]
    if s == c:
        return _row("section structure", PASS, "Same %d headings in the same order." % len(s))
    details = ["source: " + " ".join(s), "copy:   " + " ".join(c)]
    if len(c) < len(s):
        return _row("section structure", FAIL,
                    "The copy has %d heading(s), the source has %d." % (len(c), len(s)), details)
    if len(c) > len(s):
        return _row("section structure", WARN,
                    "The copy has %d heading(s), the source has %d." % (len(c), len(s)), details)
    return _row("section structure", WARN, "Same number of headings, different order or levels.", details)


def check_images(src, copy, source_lang, target):
    s, c = len(src["images"]), len(copy["images"])
    missing_alt = sum(1 for a in copy["images"] if not a)
    stale = [a for a in copy["images"] if a and langmod.guess(a) == source_lang != target]
    details = []
    status = PASS
    summary = "%d image(s), same as the source." % c
    if c < s:
        status, summary = FAIL, "The copy has %d image(s), the source has %d." % (c, s)
    elif c > s:
        status, summary = INFO, "The copy has %d image(s), the source has %d." % (c, s)
    if missing_alt:
        details.append("%d image(s) have no alt text." % missing_alt)
    if stale:
        details += ["alt text still in %s: %s" % (source_lang, a[:100]) for a in stale]
    if status == PASS and details:
        status, summary = WARN, summary + " Alt text needs attention."
    return _row("images", status, summary, details)


def check_price(src, copy, expected):
    got = copy["price"]
    if expected is not None:
        if got is None:
            return _row("price", FAIL, "No price found on the copy; expected %.2f." % expected)
        if abs(got - expected) > 0.005:
            return _row("price", FAIL, "The copy shows %.2f, expected %.2f." % (got, expected))
        return _row("price", PASS, "The copy shows the expected price, %.2f." % got)
    if got is None:
        return _row("price", WARN, "No price found on the copy.")
    return _row("price", INFO, "Source %s, copy %s. Pass --price to enforce a figure."
                % (src["price_raw"] or "none", copy["price_raw"]))


def check_buy(src, copy):
    if copy["buy"]:
        return _row("buy control", PASS, "The copy has a cart form, cart link or buy button.")
    if src["buy"]:
        return _row("buy control", FAIL, "The source has a way to buy; none was found on the copy.")
    return _row("buy control", INFO, "Neither page has a recognisable buy control.")


def check_meta(src, copy):
    problems = []
    for field in ("title", "description"):
        if not copy[field]:
            problems.append("The copy has no %s." % field)
        elif src[field] and copy[field] == src[field] and len(langmod.words(copy[field])) > 2:
            problems.append("The %s is identical to the source: %s" % (field, copy[field][:100]))
    if problems:
        return _row("search title and description", WARN, "%d issue(s)." % len(problems), problems)
    return _row("search title and description", PASS, "Both are present and differ from the source.")


def compare(src, copy, target, expected_price=None, source_lang=None, ignore=()):
    source_lang = source_lang or _page_lang(src)
    rows = [
        check_language(src, copy, target),
        check_structure(src, copy),
        check_images(src, copy, source_lang, target),
        check_price(src, copy, expected_price),
        check_buy(src, copy),
        check_meta(src, copy),
    ]
    if source_lang and source_lang != target:
        rows.insert(1, check_leftovers(src, copy, target, source_lang, ignore))
        rows.insert(2, check_identical(src, copy, ignore))
    else:
        rows.insert(1, _row("leftover source text", INFO,
                            "Skipped: source language unknown or equal to the target."))
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in (PASS, WARN, FAIL, INFO)}
    return {"source": src["source"], "copy": copy["source"], "source_lang": source_lang, "target_lang": target,
            "rows": rows, "counts": counts, "ok": counts[FAIL] == 0}
