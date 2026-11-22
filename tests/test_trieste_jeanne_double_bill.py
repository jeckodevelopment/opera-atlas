"""Trieste Jeanne double bill: two authored works, six ticketed performances."""
import json
import unittest
from pathlib import Path
from scripts.publish_catalog_v2 import ROOT
from opera_atlas.trieste_jeanne_program import (
    verified_program, SOURCE_KEY, SOURCE_URL, SCHEDULE_URL, COMPONENTS)
from opera_atlas.programs import program_from_evidence


class TriesteJeanneDoubleBillTests(unittest.TestCase):
    def test_six_source_verified_dates_for_two_works(self):
        heading,components,facts=verified_program(source_key=SOURCE_KEY,source_url=SOURCE_URL)
        self.assertEqual(len(components),2)
        self.assertEqual(len(facts),12)
        self.assertEqual(set((x["title"],x["composer"]) for x in components),set(COMPONENTS))
        dates={}
        for fact in facts:
            dates.setdefault(fact["date"],set()).add(fact["starts_at"])
        self.assertEqual(len(dates),6)
        self.assertTrue(all(len(clocks)==1 for clocks in dates.values()))
        self.assertEqual(next(iter(dates["2027-04-09"])),"2027-04-09T20:00:00+02:00")
        self.assertEqual(next(iter(dates["2027-04-18"])),"2027-04-18T16:00:00+02:00")

    def test_single_tickets_and_separate_component_identities(self):
        heading,components,facts=verified_program(source_key=SOURCE_KEY,source_url=SOURCE_URL)
        registry=json.loads((ROOT/"data"/"identity-registry.json").read_text(encoding="utf-8"))
        detail={"source_key":SOURCE_KEY,"source_url":SOURCE_URL,
                "status":"needs_program_review","program_heading":heading,
                "program_components":components,"event_facts":facts}
        bill=program_from_evidence(
            heading=heading,source_key=SOURCE_KEY,source_url=SOURCE_URL,
            candidate={"source_key":SOURCE_KEY,"official_url":SOURCE_URL},
            detail=detail,registry=registry,venue="Teatro Lirico Giuseppe Verdi",
            city="Trieste",region="Friuli-Venezia Giulia")
        self.assertEqual(len(bill["components"]),2)
        self.assertEqual(len(bill["performances"]),6)
        self.assertEqual(len({x["id"] for x in bill["performances"]}),6)
        self.assertNotEqual(bill["components"][0]["title"],bill["components"][1]["title"])

    def test_rejects_any_other_source_or_season(self):
        for key,url in ((SOURCE_KEY,SOURCE_URL.replace("jeanne-dark","another")),
                        ("verdi-trieste-season-2027-28",SOURCE_URL)):
            with self.assertRaises(ValueError):
                verified_program(source_key=key,source_url=url)


if __name__=="__main__":
    unittest.main()
