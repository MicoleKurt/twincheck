"""Command line: twincheck compare SOURCE COPY --lang fr [--price 68.90] [--html report.html]"""
import argparse
import json
import os
import sys

from . import __version__, compare, extract, lang, report

EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")


def _run(args):
    if args.lang not in lang.STOPWORDS:
        sys.exit("Unknown language '%s'. Supported: %s" % (args.lang, ", ".join(sorted(lang.STOPWORDS))))
    try:
        src, copy = extract.read(args.source), extract.read(args.copy)
    except Exception as exc:  # network errors, missing files
        sys.exit("Could not read a page: %s" % exc)
    result = compare.compare(src, copy, args.lang, expected_price=args.price,
                             source_lang=args.source_lang, ignore=args.ignore or ())
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(report.html_page(result))
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else report.text(result))
    if args.html and not args.json:
        print("HTML report: %s" % args.html)
    return 0 if result["ok"] else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="twincheck", description="Check a translated copy of a page against its source.")
    p.add_argument("--version", action="version", version="twincheck " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="compare a copy with its source")
    c.add_argument("source", help="URL or HTML file of the original page")
    c.add_argument("copy", help="URL or HTML file of the translated copy")
    c.add_argument("--lang", required=True, help="language the copy should be in, e.g. fr")
    c.add_argument("--source-lang", help="language of the source (guessed when omitted)")
    c.add_argument("--price", type=float, help="price the copy must show")
    c.add_argument("--ignore", action="append", help="text to skip, such as a brand name (repeatable)")
    c.add_argument("--html", help="also write an HTML report to this file")
    c.add_argument("--json", action="store_true", help="print JSON instead of text")
    d = sub.add_parser("demo", help="run on the bundled example pages")
    d.add_argument("--good", action="store_true", help="use the clean copy instead of the broken one")
    args = p.parse_args(argv)
    if args.cmd == "demo":
        args.source = os.path.join(EXAMPLES, "source-de.html")
        args.copy = os.path.join(EXAMPLES, "copy-fr-good.html" if args.good else "copy-fr-broken.html")
        args.lang, args.source_lang, args.price = "fr", None, 68.90
        args.ignore, args.html, args.json = ["Lumera"], None, False
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())
