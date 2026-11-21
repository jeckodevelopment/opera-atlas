"""Any approved provider can create a documented opera via the shared authority engine."""
import copy
import json
import unittest
from datetime import date
from scripts.auto_catalogue import official_identity_candidates,promote_new_works
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.auto_catalogue import SOURCE_ALLOWLIST
from scripts.publish_work_posters import load_archival_art

EXPECTED={"Le nozze di Figaro":6,"Fidelio":5,"Zenobia":4,"Arlecchino":4}
SOURCE="petruzzelli-opera-2027"

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class SourceIndependentPromotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=read(MANIFEST)
        cls.registry=read(REGISTRY)
        cls.details=read(EVIDENCE)
        cls.candidates=read(CANDIDATES)
        cls.editorial=read(EDITORIAL)
        cls.history=read(HISTORY)
        cls.urls=read(SOURCE_ALLOWLIST)["urls"]

    def test_recovered_petruzzelli_operas_promote_by_shared_rules(self):
        known={(normalized(w["title"]),normalized(w["composer"]))
               for w in self.registry["works"].values()}
        source_rows=[r for r in self.details["evidence"]
                     if r.get("source_key")==SOURCE
                     and r.get("status")=="needs_editorial_review"
                     and r.get("event_facts")]
        selected={r["event_facts"][0]["event_title"]:r for r in source_rows
                  if r["event_facts"][0]["event_title"] in EXPECTED}
        self.assertEqual(set(selected),set(EXPECTED))
        self.assertTrue(all(len(selected[title]["event_facts"])==count
                            for title,count in EXPECTED.items()))
        intelligence=official_identity_candidates(
            self.details,self.candidates,{"schema_version":1,"works":[]})
        candidate_rows={x["title"]:x for x in intelligence["works"]
                        if x["source_key"]==SOURCE and x["title"] in EXPECTED}
        self.assertEqual(set(candidate_rows),set(EXPECTED))
        self.assertTrue(all(x["official_authority_url"]==x["source_url"]
                            for x in candidate_rows.values()))
        archival=load_archival_art({"le-nozze-di-figaro","fidelio","zenobia","arlecchino"})
        self.assertEqual(len(archival),4)
        output=promote_new_works(
            self.facts,self.registry,self.details,self.candidates,
            intelligence,self.editorial,self.urls,today=date(2026,11,21),
            history=self.history,require_image=True)
        facts,registry,urls,editorial,history,report=output
        remaining={name:count for name,count in EXPECTED.items()
                   if (normalized(name),
                       normalized(candidate_rows[name]["composer"])) not in known}
        self.assertEqual(report["new_works"],len(remaining))
        self.assertEqual(report["new_recite"],sum(remaining.values()))
        for name,count in EXPECTED.items():
            rows=[p for p in facts["productions"] if p["municipality"]=="Bari"
                  and p["venue"]=="Teatro Petruzzelli"
                  and normalized(p["title"])==normalized(name)]
            self.assertEqual(len(rows),1)
            self.assertEqual(len(rows[0]["dates"]),count)
        again=promote_new_works(facts,registry,self.details,self.candidates,
             intelligence,editorial,urls,today=date(2026,11,21),
             history=history,require_image=True)
        self.assertEqual(again[-1]["new_recite"],0)

    def test_unsafe_identity_is_never_accepted(self):
        evidence=copy.deepcopy(self.details)
        source=next(r for r in evidence["evidence"] if r.get("source_key")==SOURCE
                    and r.get("event_facts", [{}])[0].get("event_title")=="Fidelio")
        source["event_facts"][0]["composer"]="Different Composer"
        result=official_identity_candidates(
            evidence,self.candidates,{"schema_version":1,"works":[]})
        self.assertFalse(any(x["candidate_id"]==source["candidate_id"]
                             for x in result["works"]))
        evidence=copy.deepcopy(self.details)
        source=next(r for r in evidence["evidence"] if r.get("source_key")==SOURCE
                    and r.get("event_facts", [{}])[0].get("event_title")=="Fidelio")
        source["status"]="needs_program_review"
        result=official_identity_candidates(
            evidence,self.candidates,{"schema_version":1,"works":[]})
        self.assertFalse(any(x["candidate_id"]==source["candidate_id"]
                             for x in result["works"]))

if __name__=="__main__":
    unittest.main()
