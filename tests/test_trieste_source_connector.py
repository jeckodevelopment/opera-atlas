"""Official Teatro Verdi Trieste connector regression tests."""
import json
import unittest

from opera_atlas.trieste_detail_parser import parse_detail
from scripts.discover_season_indexes import CONFIG, extract, eligible, validate_config
from scripts.collect_candidate_details import parse_source_credited_opera_detail

INDEX_URL = "https://www.teatroverdi-trieste.com/it/calendario-spettacoli/?a=0&t=lirica"
DETAIL_URL = "https://www.teatroverdi-trieste.com/it/spettacoli/lohengrin/"
SOURCE_KEY = "verdi-trieste-season-2026-27"

DETAIL = """
<html><main>
Richard Wagner
<h1>Lohengrin</h1>
<p>13, 14, 15, 20, 21, 22 novembre 2026</p>
<h2>Informazioni</h2><p>STAGIONE LIRICA E DI BALLETTO 2026-27</p>
<p>Musica e libretto di Richard Wagner</p>
<p>Ed. musicali: Schott Music</p>
<h2>Personaggi e interpreti</h2><p>Lohengrin, 13, 20, 22/XI</p>
<h2>Altre info</h2>
<p>A Venerdì 13 novembre 2026 ore 17.00</p>
<p>S Sabato 14 novembre 2026 ore 15.00</p>
<p>D Domenica 15 novembre 2026 ore 15.00</p>
<p>C Venerdì 20 novembre 2026 ore 17.00</p>
<p>B Sabato 21 novembre 2026 ore 17.00</p>
<p>E Domenica 22 novembre 2026 ore 15.00</p>
<h2>* DURATA</h2><p>Five hours</p>
<h2>Foto Gallery</h2>
</main></html>
"""

class TriesteSourceTests(unittest.TestCase):
    def test_official_index_is_allowlisted(self):
        sources = validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        source = next(s for s in sources if s["key"] == SOURCE_KEY)
        self.assertEqual(source["url"], INDEX_URL)
        self.assertEqual(source["min_links"], 6)
        self.assertTrue(eligible(SOURCE_KEY, DETAIL_URL))
        self.assertFalse(eligible(SOURCE_KEY,
                         "https://www.teatroverdi-trieste.com/it/news/lohengrin/"))
        # Host restrictions are enforced by index extraction and detail parsing.

    def test_index_selects_only_official_productions(self):
        entries = ["lohengrin", "don-giovanni", "lelisir-damore",
                   "la-boheme", "jeanne-darc", "aida", "norma"]
        page = "<html>" + "".join(
            '<a href="/it/spettacoli/%s/">opera</a>' % slug
            for slug in entries
        ) + '<a href="/it/news/other/">news</a>' + (
            '<a href="https://example.org/it/spettacoli/not-ours/">external</a>'
        ) + "</html>"
        links = extract(SOURCE_KEY, INDEX_URL, page, 6)
        self.assertEqual(len(links), 7)
        self.assertTrue(all(url.startswith(
            "https://www.teatroverdi-trieste.com/it/spettacoli/") for url in links))

    def test_primary_composer_and_exact_clock_only(self):
        title, composer, venue, dates = parse_detail(DETAIL, url=DETAIL_URL)
        self.assertEqual((title, composer, venue),
                         ("Lohengrin", "Richard Wagner", "Teatro Lirico Giuseppe Verdi"))
        self.assertEqual(len(dates), 6)
        self.assertEqual(dates[0], ("2026-11-13", "17:00"))
        self.assertEqual(dates[-1], ("2026-11-22", "15:00"))
        facts = parse_source_credited_opera_detail(SOURCE_KEY, DETAIL_URL, DETAIL)
        self.assertEqual(len(facts), 6)
        self.assertEqual(facts[-1]["starts_at"], "2026-11-22T15:00:00+01:00")

    def test_does_not_infer_unverified_time_or_identity(self):
        with self.assertRaises(ValueError):
            parse_detail(DETAIL.replace("Musica e libretto di Richard Wagner",
                                        "Musica anonima"), url=DETAIL_URL)
        with self.assertRaises(ValueError):
            parse_detail(DETAIL.replace("ore 17.00", "ore ??")
                               .replace("ore 15.00", "ore ??"),
                         url=DETAIL_URL)
        with self.assertRaises(ValueError):
            parse_detail(DETAIL, url=DETAIL_URL.replace(
                "www.teatroverdi-trieste.com", "not-official.example"))
        with self.assertRaises(ValueError):
            parse_detail(DETAIL.replace("A Venerdì 13 novembre 2026 ore 17.00",
                                        "A Venerdì 13 novembre 2026 ore 17.00 ANNULLATA"),
                         url=DETAIL_URL)


if __name__ == "__main__":
    unittest.main()
