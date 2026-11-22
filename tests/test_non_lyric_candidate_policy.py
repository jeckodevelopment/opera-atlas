"""Editorial policy: lyric opera, operetta and dramatic oratorio are eligible."""
import unittest
from scripts.discover_season_indexes import classify, eligible
from scripts.reconcile_published_candidates import reconcile

VANISHINGS_KEY="modena-teatro-opera-2026-27"
VANISHINGS_URL=("https://www.teatrocomunalemodena.it/spettacolo/"
                "leos-janacek-thomas-ades-vanishings/")
ALLOWED=(
    ("lirico-cagliari-opera-2027",
     "https://www.liricocagliari.it/evento/candide/"),
    ("verdi-trieste-season-2026-27",
     "https://www.teatroverdi-trieste.com/it/spettacoli/jeanne-darc-au-bucher-jeanne-dark/"),
    ("modena-teatro-opera-2026-27",
     "https://www.teatrocomunalemodena.it/spettacolo/daniele-furlati-i-salvatori-della-mezzanotte/"),
)

class EditorialGenrePolicyTests(unittest.TestCase):
    def test_composite_nonopera_excluded_even_if_previously_published(self):
        self.assertFalse(eligible(VANISHINGS_KEY,VANISHINGS_URL))
        self.assertEqual(classify(VANISHINGS_KEY,VANISHINGS_URL,{VANISHINGS_URL}),
                         "excluded_nonopera")
        rows={"schema_version":1,"candidates":[
            {"id":"one","source_key":VANISHINGS_KEY,"official_url":VANISHINGS_URL,
             "status":"needs_review"}]}
        result,_=reconcile(rows,{VANISHINGS_URL})
        self.assertEqual(result["candidates"][0]["status"],"excluded_nonopera")

    def test_operetta_oratorio_and_original_contemporary_opera_remain_eligible(self):
        for key,url in ALLOWED:
            with self.subTest(source=key):
                self.assertTrue(eligible(key,url))
                self.assertEqual(classify(key,url,set()),"needs_review")

    def test_candide_remains_reviewable_with_verified_cagliari_season(self):
        key,url=ALLOWED[0]
        rows={"schema_version":1,"candidates":[
            {"id":"one","source_key":key,"official_url":url,"status":"needs_review"}]}
        result,_=reconcile(rows,set(),cagliari_season_urls={url})
        self.assertEqual(result["candidates"][0]["status"],"needs_review")

if __name__=="__main__":
    unittest.main()
