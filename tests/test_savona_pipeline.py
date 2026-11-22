"""Savona homepage is a single approved recurring source, not a venue or one work."""
import json
import unittest

from scripts.discover_season_indexes import CONFIG, eligible, extract, validate_config, classify
from scripts.collect_candidate_details import parse_source_credited_opera_detail, selected_candidates
from scripts.source_automation import INDEX_VENUES
from opera_atlas.savona_opera_giocosa_parser import URL

KEY="savona-giocosa-rolling-opera"
HTML="""<h2>Stagione lirica autunnale 2027</h2>
<p>Opera 23 Ottobre - ore 20:00 25 Ottobre - ore 15:30 Teatro Chiabrera
Savona La traviata di Giuseppe Verdi</p>
<p>Opera 7 Novembre - ore 18:00 Teatro Chiabrera Savona
I salvatori della mezzanotte di Daniele Furlati</p>
<p>Concerto 13 Dicembre - ore 21:00 Teatro Chiabrera Savona
Te Deum di Marc-Antoine Charpentier</p>
<h2>Stagione lirica estiva 2027</h2>
<p>Opera 25 Giugno - ore 21:15 Fortezza del Priàmar Savona
Nabucco di Giuseppe Verdi</p>"""

class SavonaPipelineTests(unittest.TestCase):
    def test_registered_evergreen_official_source(self):
        src=next(x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
                 if x["key"]==KEY)
        self.assertEqual(src["url"],URL)
        self.assertEqual(src["min_links"],1)
        self.assertEqual(INDEX_VENUES[KEY],("Savona|Teatro Gabriello Chiabrera",))
        self.assertTrue(eligible(KEY,URL))
        for invalid in ("http://operagiocosa.it/",
                        "https://other.invalid/",
                        "https://operagiocosa.it/?q=node/15"):
            self.assertFalse(eligible(KEY,invalid))
        policy=json.loads(open("data/season-lifecycle-policy.json",encoding="utf-8").read())
        self.assertEqual(policy["sources"][KEY]["strategy"],"evergreen_index")

    def test_index_and_first_party_detail_in_common_pipeline(self):
        self.assertEqual(extract(KEY,URL,HTML,1),[URL])
        facts=parse_source_credited_opera_detail(KEY,URL,HTML)
        self.assertEqual(len(facts),3)
        self.assertEqual({x["event_title"] for x in facts},
                         {"La traviata","I salvatori della mezzanotte"})
        self.assertTrue(all(x["venue"]=="Teatro Chiabrera" for x in facts))
        self.assertTrue(all(x["date"].startswith("2027-") for x in facts))
        self.assertTrue(all(x["starts_at"].endswith(("+01:00","+02:00")) for x in facts))
        self.assertEqual(classify(KEY,URL,{URL}),"needs_review")

    def test_multiwork_homepage_splits_without_venue_confusion(self):
        from scripts.auto_catalogue import split_verified_season
        rows=parse_source_credited_opera_detail(KEY,URL,HTML)
        item={"source_key":KEY,"source_url":URL,"event_facts":rows,
              "status":"needs_editorial_review"}
        groups=split_verified_season(item)
        self.assertEqual([len(x["event_facts"]) for x in groups],[1,2])
        self.assertEqual({x["event_facts"][0]["event_title"] for x in groups},
                         {"La traviata","I salvatori della mezzanotte"})
        altered={**item,"event_facts":[*rows,{**rows[0],"venue":"Fortezza del Priàmar"}]}
        self.assertEqual(split_verified_season(altered),[altered])

    def test_reject_unverified_or_only_nonopera_index(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            extract(KEY,URL,"<h2>Stagione lirica autunnale 2027</h2>"
                    "<p>Concerto Teatro Chiabrera Savona Te Deum</p>",1)
        with self.assertRaises(ValueError):
            extract(KEY,URL,HTML,4)

if __name__=="__main__":
    unittest.main()
