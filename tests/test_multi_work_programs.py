"""Generalized multi-work billing and a single ticket per showtime."""
import copy
import json
import unittest
from pathlib import Path

from opera_atlas.programs import credited_components,program_from_evidence
from scripts.publish_catalog_v2 import ROOT

class MultiWorkProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        cls.evidence=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text())
        cls.candidates=json.loads((ROOT/"data/season-index-candidates.json").read_text())
        cls.details=next(x for x in cls.evidence["evidence"]
                         if x.get("status")=="needs_program_review"
                         and x.get("source_key")=="petruzzelli-opera-2027")
        cls.candidate=next(x for x in cls.candidates["candidates"]
                           if x["id"]==cls.details["candidate_id"])
        cls.heading="L’ARLÉSIENNE di Georges Bizet | PAGLIACCI di Ruggero Leoncavallo | 13-20 OTTOBRE"

    def build(self,detail=None,candidate=None,heading=None):
        detail=detail or self.details
        candidate=candidate or self.candidate
        return program_from_evidence(
            heading=heading or self.heading,
            source_key="petruzzelli-opera-2027",
            source_url=detail["source_url"],
            candidate=candidate,detail=detail,registry=self.registry,
            venue="Teatro Petruzzelli",city="Bari",region="Puglia")

    def test_one_program_with_two_independent_works_and_seven_recite(self):
        bill=self.build()
        self.assertEqual(bill["title"],"L’ARLÉSIENNE / PAGLIACCI")
        self.assertEqual(len(bill["components"]),2)
        self.assertEqual(bill["components"][0]["composer"],"Georges Bizet")
        self.assertIsNone(bill["components"][0]["work_id"])
        self.assertEqual(bill["components"][1]["composer"],"Ruggero Leoncavallo")
        self.assertEqual(bill["components"][1]["work_id"],"oa-w-000006")
        self.assertEqual(len(bill["performances"]),7)
        self.assertEqual(len({p["id"] for p in bill["performances"]}),7)
        self.assertEqual(self.build(),bill)

    def test_generic_shared_schedule_no_duplicate_tickets(self):
        detail=copy.deepcopy(self.details)
        detail["source_key"]="teatro-grande-opera-2026"
        detail["source_url"]="https://teatrogrande.it/it/stagioni/2026/cavalleria-rusticana-pagliacci"
        detail["program_heading"]="Cavalleria Rusticana/Pagliacci di Pietro Mascagni/Ruggero Leoncavallo"
        detail["program_components"]=[
            {"title":"Cavalleria rusticana","composer":"Pietro Mascagni"},
            {"title":"Pagliacci","composer":"Ruggero Leoncavallo"}]
        detail["event_facts"]=[
            {"event_title":part["title"],"composer":part["composer"],
             "date":day,"starts_at":stamp,"venue":"Teatro Grande"}
            for day,stamp in (("2026-12-11","2026-12-11T20:00:00+01:00"),
                              ("2026-12-13","2026-12-13T15:30:00+01:00"))
            for part in detail["program_components"]]
        candidate={"source_key":detail["source_key"],"official_url":detail["source_url"]}
        def build(d):
            return program_from_evidence(
                heading=d["program_heading"],source_key=d["source_key"],
                source_url=d["source_url"],candidate=candidate,detail=d,
                registry=self.registry,venue="Teatro Grande",
                city="Brescia",region="Lombardia")
        bill=build(detail)
        self.assertEqual(len(bill["components"]),2)
        self.assertEqual(len(bill["performances"]),2)
        bad=copy.deepcopy(detail)
        bad["event_facts"][-1]["starts_at"]="2026-12-13T16:00:00+01:00"
        with self.assertRaises(ValueError):build(bad)

    def test_reject_incomplete_or_ambiguous_credits(self):
        for heading in ("Pagliacci di Ruggero Leoncavallo",
                        "Pagliacci di Ruggero Leoncavallo | Pagliacci di Ruggero Leoncavallo",
                        "L’Arlésienne | Pagliacci di Ruggero Leoncavallo",
                        "Pagliacci di Ruggero Leoncavallo | 13-20 OTTOBRE"):
            with self.subTest(heading=heading),self.assertRaises(ValueError):
                credited_components(heading)

    def test_different_source_or_duplicate_ticket_is_blocked(self):
        candidate=copy.deepcopy(self.candidate)
        candidate["official_url"]="https://example.org/fake/"
        with self.assertRaises(ValueError):
            self.build(candidate=candidate)
        detail=copy.deepcopy(self.details)
        detail["event_facts"].append(copy.deepcopy(detail["event_facts"][0]))
        with self.assertRaises(ValueError):
            self.build(detail=detail)
        detail=copy.deepcopy(self.details)
        detail["event_facts"][0]["venue"]="Another Theatre"
        with self.assertRaises(ValueError):
            self.build(detail=detail)

if __name__=="__main__":
    unittest.main()
