"""Other-season Rome links are audited, never published as 2026/27 operas."""
import unittest
from opera_atlas.roma_detail_parser import official_rome_other_season
from scripts.reconcile_published_candidates import (
    reconcile,verified_other_season_evidence)

URL="https://www.operaroma.it/spettacoli/falstaff/"
SOURCE="opera-roma-season-2026-27"

def official(season):
    return ("<nav><a>Stagione 2026/2027</a></nav>"
            "<p>Stagione "+season+"</p>"
            "<h1>Falstaff</h1><p>Musica di Giuseppe Verdi</p>"
            "<h3>Le date</h3><p>venerdì 30 Ott ORE 20:00</p>"
            "<footer>Stagione 2025/2026 e Stagione 2026/2027</footer>")

class SourceScopedSeasons(unittest.TestCase):
    def test_positive_official_other_season_and_recommendation_exclusion(self):
        self.assertEqual(official_rome_other_season(official("2025/2026"),url=URL),
                         "2025/2026")
        self.assertIsNone(official_rome_other_season(official("2026/2027"),url=URL))
        self.assertIsNone(official_rome_other_season(
            "<h1>Falstaff</h1><p>Stagione 2025/2026</p>",url=URL))
        self.assertIsNone(official_rome_other_season(
            "<nav>Stagione 2025/2026</nav><h1>Falstaff</h1>",url=URL))
        with self.assertRaises(ValueError):
            official_rome_other_season(official("2025/2026"),
                                       url="https://example.com/spettacoli/falstaff/")

    def test_reconcile_only_source_verified_older_season(self):
        cand={"schema_version":1,"candidates":[
            {"id":"old","source_key":SOURCE,"official_url":URL,
             "status":"needs_review"},
            {"id":"active","source_key":SOURCE,
             "official_url":"https://www.operaroma.it/spettacoli/la-rondine/",
             "status":"needs_review"},
            {"id":"unknown","source_key":SOURCE,
             "official_url":"https://www.operaroma.it/spettacoli/unknown/",
             "status":"needs_review"}]}
        evidence={"evidence":[{"candidate_id":"old","source_key":SOURCE,
            "source_url":URL,"status":"out_of_monitored_season",
            "official_season":"2025/2026","content_sha256":"a"*64}]}
        older=verified_other_season_evidence(evidence)
        self.assertEqual(older,{(SOURCE,URL)})
        result,health=reconcile(cand,{"https://www.operaroma.it/spettacoli/la-rondine/"},
                                other_season_urls=older)
        self.assertEqual({r["id"]:r["status"] for r in result["candidates"]},
                         {"old":"not_in_official_season","active":"already_catalogued",
                          "unknown":"needs_review"})
        again,_=reconcile(result,{"https://www.operaroma.it/spettacoli/la-rondine/"},
                          other_season_urls=older)
        self.assertEqual(result,again)
        published,_=reconcile(result,{URL},other_season_urls=older)
        self.assertEqual(published["candidates"][0]["status"],"already_catalogued")
        evidence["evidence"][0]["source_key"]="untrusted-other-source"
        self.assertFalse(verified_other_season_evidence(evidence))
        evidence["evidence"][0]["source_key"]=SOURCE
        evidence["evidence"][0]["content_sha256"]="unsigned"
        self.assertFalse(verified_other_season_evidence(evidence))

if __name__=="__main__":
    unittest.main()
