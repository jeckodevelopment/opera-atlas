"""Candidate collection must use the source's strict venue/composer parser."""
import unittest
from datetime import date
from unittest.mock import patch

from opera_atlas.controlled_fetch import FetchResult
from scripts.collect_candidate_details import collect

VICENZA = "https://www.vicenzainlirica.it/il-barbiere-di-siviglia-rossini/"
MANTOVA = "https://www.teatrosocialemantova.it/it-it/tosca.aspx"
TAORMINA = "https://www.taorminaoperafestival.org/la-traviata-2025/"

class StrictVenueCandidateCollectionTests(unittest.TestCase):
    def collect_one(self, key, url, html):
        queue={"schema_version":1,"candidates":[{
            "id":"test-"+key,"source_key":key,"official_url":url,
            "status":"needs_review"}]}
        def fetch(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"a"*64,100)
        return collect(queue,{"schema_version":1,"evidence":[]},
                       network_enabled=True,fetcher=fetch,
                       today=date(2026,11,23))

    def test_vicenza_real_venue_and_public_recitals_are_extracted(self):
        html=('<h1>Il barbiere di Siviglia – Rossini</h1>'
              '<p>Vicenza in Lirica 2026</p>'
              '<p>Giovedì 10 settembre | ore 20.30</p>'
              '<p>Teatro Olimpico di Vicenza</p>'
              '<p>opera buffa in 2 atti</p><p>musica di G. ROSSINI</p>')
        evidence,health=self.collect_one(
            "vicenza-olimpico-rolling-opera",VICENZA,html)
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        fact=evidence["evidence"][0]["event_facts"][0]
        self.assertEqual(fact["event_title"],"Il barbiere di Siviglia")
        self.assertEqual(fact["venue"],"Teatro Olimpico")
        self.assertEqual(fact["starts_at"],"2026-09-10T20:30:00+02:00")

    def test_vicenza_touring_venue_does_not_fall_back_to_generic_event(self):
        html=('<h1>Il barbiere di Siviglia – Rossini</h1>'
              '<p>Vicenza in Lirica 2026</p>'
              '<p>Giovedì 10 settembre | ore 20.30</p>'
              '<p>Villa Pisani Bonetti di Lonigo</p>'
              '<p>opera buffa in 2 atti</p><p>musica di G. ROSSINI</p>')
        _,health=self.collect_one("vicenza-olimpico-rolling-opera",VICENZA,html)
        self.assertEqual(health[0]["reason"],"no_verified_showtimes",health)
        self.assertTrue(any("staged elsewhere" in x
                            for x in health[0]["diagnostic"]))

    def test_mantova_taormina_use_first_party_parser_not_generic_fallback(self):
        for key,url in (
            ("mantova-sociale-rolling-opera",MANTOVA),
            ("taormina-opera-festival-rolling",TAORMINA),
        ):
            with self.subTest(key=key):
                with patch("scripts.collect_candidate_details.parse_source_credited_opera_detail",
                           side_effect=ValueError("strict venue evidence missing")) as strict, \
                     patch("scripts.collect_candidate_details.parse_event_facts",
                           side_effect=AssertionError("generic Event bypass")):
                    _,health=self.collect_one(key,url,"<h1>Unverified listing</h1>")
                self.assertEqual(health[0]["reason"],"no_verified_showtimes")
                self.assertIn("official_composer_credit:strict venue evidence missing",
                              health[0]["diagnostic"])
                strict.assert_called_once()

if __name__=="__main__":
    unittest.main()
