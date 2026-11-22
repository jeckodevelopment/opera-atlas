"""Actual Novara outdoor opera venues must not be recast as Teatro Coccia."""
import json
import unittest
from scripts.auto_catalogue import verified_venue,ensure_venue
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.publish_catalog_v2 import REGISTRY

class NovaraNattaVenueTests(unittest.TestCase):
    def test_official_venue_evidence_allocates_own_piemontese_location(self):
        doc=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        row=next(x for x in doc["evidence"]
                 if x["source_url"]==
                 "https://www.fondazioneteatrococcia.it/stagione-27-il-noce-di-benevento.html")
        self.assertEqual(row["status"],"needs_editorial_review")
        facts=row["event_facts"]
        self.assertEqual(len(facts),2)
        self.assertEqual({f["venue"] for f in facts},{"Giardini di Palazzo Natta"})
        reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
        resolved=verified_venue("coccia-novara-rolling-opera",facts,reg)
        self.assertEqual(resolved[:2],("Novara","Giardini di Palazzo Natta"))
        venue=ensure_venue(reg,*resolved)
        self.assertEqual(venue["city"],"Novara")
        self.assertEqual(venue["region"],"Piemonte")
        self.assertEqual(venue["name"],"Giardini di Palazzo Natta")
        self.assertEqual(verified_venue(
            "coccia-novara-rolling-opera",facts,reg)[2]["id"],venue["id"])
        for bad in ("Teatro Verdi","Piccolo Coccia",None):
            rows=[{**f,"venue":bad} for f in facts]
            self.assertIsNone(verified_venue("coccia-novara-rolling-opera",rows,reg))
        # A Coccia show must never automatically relocate to Natta.
        melograno=next(x for x in doc["evidence"]
                       if x["source_url"].endswith("stagione-27-dove-nasce-il-melograno.html"))
        self.assertEqual(verified_venue(
            "coccia-novara-rolling-opera",melograno["event_facts"],reg)[:2],
            ("Novara","Teatro Coccia"))

if __name__=="__main__":
    unittest.main()
