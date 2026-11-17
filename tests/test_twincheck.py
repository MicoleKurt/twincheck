import os
import unittest

from twincheck import cli, compare, extract, lang, report

EX = cli.EXAMPLES
SRC = os.path.join(EX, "source-de.html")
GOOD = os.path.join(EX, "copy-fr-good.html")
BAD = os.path.join(EX, "copy-fr-broken.html")


def run(copy, **kw):
    kw.setdefault("ignore", ["Lumera"])
    return compare.compare(extract.read(SRC), extract.read(copy), "fr", **kw)


def status(result, check):
    return next(r for r in result["rows"] if r["check"] == check)["status"]


class Lang(unittest.TestCase):
    def test_guess(self):
        self.assertEqual(lang.guess("Die Lieferung ist für Sie kostenlos und nicht teuer"), "de")
        self.assertEqual(lang.guess("La livraison est gratuite pour vous et très rapide"), "fr")
        self.assertEqual(lang.guess("The delivery is free for you and it is fast"), "en")

    def test_too_short_is_unknown(self):
        self.assertIsNone(lang.guess("42 cm"))
        self.assertIsNone(lang.guess("Lumera"))


class Extract(unittest.TestCase):
    def test_reads_source(self):
        p = extract.read(SRC)
        self.assertEqual(p["lang"], "de")
        self.assertEqual([t for t, _ in p["headings"]], ["h1", "h2", "h2", "h2", "h3", "h3"])
        self.assertEqual(len(p["images"]), 3)
        self.assertEqual(p["price"], 73.9)
        self.assertTrue(p["buy"])

    def test_script_text_is_not_page_text(self):
        self.assertFalse(any("priceCurrency" in x for _, x in extract.read(SRC)["blocks"]))

    def test_price_formats(self):
        cases = {"CHF 68.90": 68.9, "68,90 €": 68.9, "1.299,00": 1299.0, "1,299.00": 1299.0,
                 "690 kr": 690.0, "€74": 74.0, "": None, None: None, "free": None}
        for raw, want in cases.items():
            self.assertEqual(extract.to_number(raw), want, raw)


class Compare(unittest.TestCase):
    def test_good_copy_passes(self):
        r = run(GOOD, expected_price=68.90)
        self.assertTrue(r["ok"], report.text(r))
        self.assertEqual(r["counts"]["fail"], 0)
        self.assertEqual(r["counts"]["warn"], 0, report.text(r))
        self.assertEqual(r["source_lang"], "de")

    def test_broken_copy_fails_each_check(self):
        r = run(BAD, expected_price=68.90)
        self.assertFalse(r["ok"])
        for check in ("leftover source text", "section structure", "images", "price", "buy control"):
            self.assertEqual(status(r, check), "fail", check)
        for check in ("language tag", "search title and description", "identical short strings"):
            self.assertEqual(status(r, check), "warn", check)

    def test_leftovers_name_the_blocks(self):
        row = next(x for x in run(BAD)["rows"] if x["check"] == "leftover source text")
        self.assertEqual(len(row["details"]), 2)
        self.assertTrue(any("Der Aufbau" in d for d in row["details"]))

    def test_price_without_expectation_is_info(self):
        self.assertEqual(status(run(GOOD), "price"), "info")

    def test_wrong_price_fails(self):
        self.assertEqual(status(run(GOOD, expected_price=70.00), "price"), "fail")

    def test_ignore_skips_brand(self):
        r = compare.compare(extract.read(SRC), extract.read(GOOD), "fr", ignore=[])
        self.assertEqual(status(r, "identical short strings"), "pass")

    def test_same_language_skips_leftovers(self):
        r = compare.compare(extract.read(SRC), extract.read(SRC), "de")
        self.assertEqual(status(r, "leftover source text"), "info")
        self.assertTrue(r["ok"])


class Output(unittest.TestCase):
    def test_reports(self):
        r = run(BAD, expected_price=68.90)
        self.assertIn("The copy is not ready.", report.text(r))
        page = report.html_page(r)
        self.assertIn("<title>twincheck report</title>", page)
        self.assertNotIn("<script", page)

    def test_exit_codes(self):
        self.assertEqual(cli.main(["demo", "--good"]), 0)
        self.assertEqual(cli.main(["demo"]), 1)

    def test_unknown_language(self):
        with self.assertRaises(SystemExit):
            cli.main(["compare", SRC, GOOD, "--lang", "xx"])


if __name__ == "__main__":
    unittest.main()
