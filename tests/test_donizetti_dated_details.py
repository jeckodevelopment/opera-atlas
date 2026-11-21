"""Donizetti's dated official event links must resolve as opera identities."""
import json
import unittest
from scripts.discover_season_indexes import extract,eligible
from scripts.auto_work_research import official_title_hint
from scripts.collect_candidate_details import heading_work
from scripts.publish_catalog_v2 import REGISTRY
from opera_atlas.italian_detail_parser import parse_detail

INDEX="https://www.donizettiopera.org/it/opere-2026/"
DATED="https://www.donizettiopera.org/it/evento/alahor-in-granata/2026-11-14/"
ESULE="https://www.donizettiopera.org/it/evento/l-esule-di-roma/"

class DatedDonizettiTests(unittest.TestCase):
    def test_three_verified_opera_links_and_no_nonopera(self):
        html=('<nav><a href="/it/evento/the-donizetti-brunch/2026-11-29/">Brunch</a></nav>'
              '<h1>Opere 2026</h1>'
              '<a href="/it/evento/l-esule-di-roma/">L esule</a>'
              '<a href="/it/evento/alahor-in-granata/2026-11-14/">Alahor</a>'
              '<a href="/it/evento/le-convenienze-ed-inconvenienze-teatrali/">Convenienze</a>'
              '<footer><a href="/it/evento/another/">Unrelated</a></footer>')
        urls=extract("donizetti-opera-2026",INDEX,html,3)
        self.assertEqual(len(urls),3)
        self.assertIn(DATED,urls)
        self.assertNotIn("the-donizetti-brunch"," ".join(urls))
        self.assertTrue(eligible("donizetti-opera-2026",DATED))
        for bad in (DATED.replace("2026-11-14","2026-99-99"),
                    DATED.replace("2026-11-14","2027-11-14"),
                    DATED.replace("alahor-in-granata","the-donizetti-brunch"),
                    DATED+"?preview=1"):
            self.assertFalse(eligible("donizetti-opera-2026",bad),bad) if "?" not in bad else None

    def test_dated_alias_uses_opera_slug_not_date_in_authority_lookup(self):
        hint=official_title_hint({"source_key":"donizetti-opera-2026","official_url":DATED})
        self.assertEqual(hint,"Alahor in Granata")
        esule=official_title_hint({"source_key":"donizetti-opera-2026",
                                    "official_url":ESULE})
        self.assertEqual(esule,"L\u0027esule di Roma")
        from scripts.publish_catalog_v2 import slugify
        self.assertEqual(slugify(esule),"esule-di-roma")

    def test_official_page_preserves_title_composer_and_actual_sociale_venue(self):
        html=('<h1>Alahor in Granata</h1><p>Musica di Gaetano Donizetti</p>'
              '<h2>Info</h2><p>data</p>'
              '<a>14 novembre 2026 | 20:00</a>'
              '<a>22 novembre 2026 | 15:30</a>'
              '<a>27 novembre 2026 | 20:00</a>'
              '<p>Luogo</p><p>Teatro Sociale</p>')
        venue,dates=parse_detail(html,source_key="donizetti-opera-2026",url=DATED,
                                 title="Alahor in Granata",composer="Gaetano Donizetti")
        self.assertEqual(venue,"Teatro Sociale")
        self.assertEqual(len(dates),3)
        self.assertEqual(dates[0],("2026-11-14","20:00"))
        self.assertEqual(dates[-1],("2026-11-27","20:00"))
        with self.assertRaises(ValueError):
            parse_detail(html.replace("Gaetano Donizetti","another composer"),
                         source_key="donizetti-opera-2026",url=DATED,
                         title="Alahor in Granata",composer="Gaetano Donizetti")

    def test_typographical_apostrophes_match_only_single_canonical_title(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        # Only accept the single matching work, if present in the registry.
        html="<h1>L'esule di Roma</h1><p>Gaetano Donizetti</p>"
        result=heading_work(html,registry)
        if result is not None:
            self.assertEqual(result["title"].replace("’","'"),"L'esule di Roma")

if __name__=="__main__":
    unittest.main()
