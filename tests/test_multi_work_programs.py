"""Generalized multi-work billing and a single ticket per showtime."""
import copy
import json
import unittest
from pathlib import Path

from opera_atlas.programs import credited_components,program_from_evidence
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_programs import load_reviewed_work_editorials, assemble_programs

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

    def test_four_reviewed_editorials_are_complete_and_unambiguous(self):
        file=ROOT/"data"/"reviewed-program-work-editorials.json"
        entries=json.loads(file.read_text(encoding="utf-8"))
        reviewed=load_reviewed_work_editorials(entries)
        expected={
            ("don pasquale","gaetano donizetti"),
            ("il tabarro","giacomo puccini"),
            ("suor angelica","giacomo puccini"),
            ("gianni schicchi","giacomo puccini"),
        }
        self.assertEqual(set(reviewed),expected)
        for profile in reviewed.values():
            self.assertTrue(profile["synopsis"])
            self.assertGreaterEqual(len(profile["history"]["sources"]),2)
        with self.assertRaises(ValueError):
            load_reviewed_work_editorials({
                "schema_version":1,"works":entries["works"]*2})
        broken=copy.deepcopy(entries)
        broken["works"][0]["history"]["sources"]=[]
        with self.assertRaises(ValueError):
            load_reviewed_work_editorials(broken)

    def test_jesi_trittico_is_one_program_with_two_tickets_and_three_editorials(self):
        read=lambda name:json.loads((ROOT/name).read_text(encoding="utf-8"))
        catalog=assemble_programs(
            read("data/season-index-candidates.json"),
            read("data/candidate-detail-evidence.json"),
            self.registry,
            read("data/verified-launch-catalog.json"),
            read("data/season-index-config.json"),
            read("data/reviewed-program-work-editorials.json"))
        matches=[p for p in catalog["programs"]
                 if p["source_key"]=="jesi-trittico-opera-2026"]
        self.assertEqual(len(matches),1)
        program=matches[0]
        self.assertEqual(len(program["performances"]),2)
        self.assertEqual(len(program["components"]),3)
        self.assertEqual({p["title"] for p in program["components"]},
                         {"Il tabarro","Suor Angelica","Gianni Schicchi"})
        self.assertTrue(all("editorial" in p for p in program["components"]))

    def test_four_canonical_reserved_ids_and_jesi_component_references(self):
        reserved=self.registry.get("reserved_works",{})
        expected={
            ("don pasquale","gaetano donizetti"):"oa-w-000090",
            ("il tabarro","giacomo puccini"):"oa-w-000091",
            ("suor angelica","giacomo puccini"):"oa-w-000092",
            ("gianni schicchi","giacomo puccini"):"oa-w-000093",
        }
        canonical=list(self.registry["works"].values())+list(reserved.values())
        self.assertEqual({(w["title"].casefold(),w["composer"].casefold()):w["id"]
                          for w in canonical
                          if w["id"] in expected.values()},expected)
        all_ids=[w["id"] for w in self.registry["works"].values()]
        self.assertFalse(set(all_ids) & {w["id"] for w in reserved.values()})
        detail=next(x for x in self.evidence["evidence"]
                    if x.get("source_key")=="jesi-trittico-opera-2026")
        candidate=next(x for x in self.candidates["candidates"]
                       if x["id"]==detail["candidate_id"])
        p=program_from_evidence(
            heading=detail["program_heading"],source_key=detail["source_key"],
            source_url=detail["source_url"],candidate=candidate,detail=detail,
            registry=self.registry,venue="Teatro Giovan Battista Pergolesi",
            city="Jesi",region="Marche")
        self.assertEqual({x["work_id"] for x in p["components"]},
                         {"oa-w-000091","oa-w-000092","oa-w-000093"})
        self.assertEqual(len(p["performances"]),2)
        self.assertEqual(len({x["id"] for x in p["performances"]}),2)

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
