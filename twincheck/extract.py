"""Read a page (URL or local file) and pull out what a duplicate must keep."""
import json
import os
import re
import urllib.request
from html.parser import HTMLParser

BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "button", "td", "th", "figcaption",
         "summary", "label", "blockquote", "dt", "dd"}
SKIP = {"script", "style", "noscript", "template", "svg"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BUY_WORDS = re.compile(
    r"\b(add to cart|buy now|order now|checkout|in den warenkorb|jetzt kaufen|bestellen|ajouter au panier|"
    r"acheter|commander|aggiungi al carrello|acquista|ordina|añadir al carrito|comprar|lägg i varukorg|köp nu|"
    r"beställ|in winkelwagen|nu kopen|lisää ostoskoriin|osta nyt|tilaa)\b", re.I)
PRICE = re.compile(r"(?:[€$£]|CHF|EUR|USD|SEK)\s?\d[\d.,]*\d|\d[\d.,]*\d\s?(?:[€$£]|CHF|EUR|USD|SEK|kr)")


def load(source, timeout=25):
    if os.path.exists(source):
        with open(source, encoding="utf-8", errors="replace") as f:
            return f.read()
    if not re.match(r"https?://", source):
        raise FileNotFoundError("not a file and not a URL: %s" % source)
    req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0 (twincheck)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.blocks = []         # [tag, text]
        self.open_blocks = []    # indexes into blocks for the BLOCK tags still open
        self.lang = None
        self.title = ""
        self.in_title = False
        self.description = ""
        self.images = []         # alt text per image, None when the attribute is missing
        self.meta_price = None
        self.jsonld = []
        self.in_jsonld = False
        self.buy = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"].split("-")[0].lower()
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.jsonld.append("")
        if tag in SKIP:
            self.skip += 1
            return
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name == "description":
                self.description = a.get("content") or ""
            if name in ("product:price:amount", "og:price:amount") and a.get("content"):
                self.meta_price = a["content"]
        elif tag == "img":
            self.images.append(a.get("alt"))
        elif tag == "form" and re.search(r"/cart|checkout", a.get("action") or "", re.I):
            self.buy = True
        elif tag == "a" and re.search(r"/cart|/checkout", a.get("href") or "", re.I):
            self.buy = True
        if tag in BLOCK:
            self.blocks.append([tag, ""])
            self.open_blocks.append(len(self.blocks) - 1)

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_jsonld = False
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "title":
            self.in_title = False
        if tag in BLOCK and self.open_blocks:
            self.open_blocks.pop()

    def handle_data(self, data):
        if self.in_jsonld:
            self.jsonld[-1] += data
        elif self.skip:
            return
        elif self.in_title:
            self.title += data
        elif data.strip():
            if self.open_blocks:
                self.blocks[self.open_blocks[-1]][1] += data
            else:
                self.blocks.append(["text", data])


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _jsonld_price(chunks):
    def walk(node):
        if isinstance(node, dict):
            offers = node.get("offers")
            for o in (offers if isinstance(offers, list) else [offers]):
                if isinstance(o, dict) and o.get("price") not in (None, ""):
                    return str(o["price"])
            node = list(node.values())
        if isinstance(node, list):
            for v in node:
                found = walk(v)
                if found:
                    return found
        return None

    for c in chunks:
        try:
            found = walk(json.loads(c))
        except ValueError:
            continue
        if found:
            return found
    return None


def to_number(price):
    """Turn 'CHF 68.90', '68,90 EUR' or '1.299,00' into 68.9 / 68.9 / 1299.0. None when unreadable."""
    if price is None:
        return None
    digits = re.sub(r"[^\d.,]", "", str(price)).strip(".,")
    if not digits:
        return None
    if "," in digits and "." in digits:
        if digits.rfind(",") > digits.rfind("."):
            digits = digits.replace(".", "").replace(",", ".")
        else:
            digits = digits.replace(",", "")
    elif "," in digits:
        head, _, tail = digits.rpartition(",")
        digits = head.replace(",", "") + "." + tail if len(tail) in (1, 2) else digits.replace(",", "")
    try:
        return round(float(digits), 2)
    except ValueError:
        return None


def read(source):
    r = _Reader()
    r.feed(load(source))
    blocks = [(t, _clean(x)) for t, x in r.blocks if _clean(x)]
    text_price = next((m.group(0) for m in (PRICE.search(x) for _, x in blocks) if m), None)
    price_raw = _jsonld_price(r.jsonld) or r.meta_price or text_price
    return {
        "source": source,
        "lang": r.lang,
        "title": _clean(r.title),
        "description": _clean(r.description),
        "blocks": blocks,
        "headings": [(t, x) for t, x in blocks if t in HEADINGS],
        "images": r.images,
        "price_raw": price_raw,
        "price": to_number(price_raw),
        "buy": r.buy or any(BUY_WORDS.search(x) for _, x in blocks if len(x) < 40),
    }
