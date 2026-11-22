"""The public program feed publishes a ticket only once, without fake operas."""
import copy
import json
import unittest
from pathlib import Path
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_programs import (
    assemble_programs,publish,OUTPUT,REVIEWED_WORKS
)
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import CONFIG,OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import REGISTRY
from scripts.build_verified_catalog import MANIFEST

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class PublicMultiWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates=read(CANDIDATES)
        cls.evidence=read(EVIDENCE)
        cls.registry=read(REGISTRY)
        cls.facts=read(MANIFEST)
        cls.config=read(CONFIG)
        cls.reviewed=read(REVIEWED_WORKS)
    def build(self,evidence=None):
        return assemble_programs(self.candidates,evidence or self.evidence,
                                 self.registry,self.facts,self.config,self.reviewed)
    def test_published_feed_matches_deterministic_verified_catalog(self):
        result=self.build()
        bill=next(x for x in result["programs"]
                  if x["source_key"]=="petruzzelli-opera-2027")
        self.assertEqual(len(bill["components"]),2)
        self.assertEqual(bill["components"][0]["composer"],"Georges Bizet")
        self.assertIsNone(bill["components"][0]["work_id"])
        self.assertEqual(bill["components"][1]["work_id"],"oa-w-000006")
        self.assertEqual(len(bill["performances"]),7)
        self.assertEqual(len({x["id"] for x in bill["performances"]}),7)
        self.assertEqual(bill["performances"][0]["starts_at"],
                         "2027-10-13T20:30:00+02:00")
        self.assertEqual(result,read(OUTPUT))
        self.assertEqual(publish(check=True),result)
    def test_conflicting_heading_or_ticket_blocks_program(self):
        wrong=copy.deepcopy(self.evidence)
        row=next(x for x in wrong["evidence"]
                 if x.get("status")=="needs_program_review"
                 and x.get("program_heading"))
        row["program_heading"]=row["program_heading"].replace(
            "Ruggero Leoncavallo","Unrelated Composer")
        with self.assertRaises(ValueError):
            self.build(wrong)
        wrong=copy.deepcopy(self.evidence)
        row=next(x for x in wrong["evidence"]
                 if x.get("status")=="needs_program_review"
                 and x.get("program_heading"))
        row["event_facts"].append(copy.deepcopy(row["event_facts"][0]))
        with self.assertRaises(ValueError):
            self.build(wrong)
    def test_catalogued_candidate_keeps_published_program(self):
        candidates=copy.deepcopy(self.candidates)
        target=next(c for c in candidates["candidates"]
                    if c["id"]==next(e["candidate_id"] for e in self.evidence["evidence"]
                                    if e.get("status")=="needs_program_review"))
        target["status"]="already_catalogued"
        from scripts.publish_programs import assemble_programs
        config=json.loads((ROOT/"data/season-index-config.json").read_text())
        feed=assemble_programs(candidates,self.evidence,self.registry,self.facts,config,self.reviewed)
        self.assertEqual(feed,self.build())

    def test_legacy_work_and_ticket_ids_unchanged(self):
        bills=self.build()["programs"]
        canonical_ids={x["id"] for x in self.registry["performances"].values()}
        program_ids={r["id"] for p in bills for r in p["performances"]}
        self.assertFalse(canonical_ids & program_ids)
        for p in bills:
            for r in p["performances"]:
                self.assertFalse(any(x["source_url"]==p["source_url"] and
                    r["local_date"] in {day for day,_ in x["dates"]}
                    for x in self.facts["productions"]))
    def test_client_and_workflow_do_not_duplicate_single_opera(self):
        client=(ROOT/"site/catalog-client.js").read_text()
        detail=(ROOT/"site/detail.js").read_text()
        index=(ROOT/"site/directory.js").read_text()
        workflow=(ROOT/".github/workflows/refresh-catalog.yml").read_text()
        self.assertIn("programPerformances(base,byWork,byVenue,performances)",client)
        self.assertIn("program_components:components",client)
        self.assertIn("selected.kind===\"program\"",detail)
        self.assertIn('section==="opere"&&e.program_id',index)
        self.assertIn("python -m scripts.publish_programs",workflow)
        self.assertIn("public/catalog/programs.json",workflow)

if __name__=="__main__":
    unittest.main()
