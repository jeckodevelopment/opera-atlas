"""TCBO six new opera identities promote all 19 official showtimes atomically."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import official_identity_candidates,promote_new_works
from scripts.publish_catalog_v2 import ROOT,REGISTRY,assemble
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY,build_editorial
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.auto_catalogue import SOURCE_ALLOWLIST

class BolognaFullSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(path):return json.loads(path.read_text(encoding="utf-8"))
        cls.facts=read(MANIFEST)
        cls.registry=read(REGISTRY)
        cls.candidates=read(CANDIDATES)
        cls.evidence=read(EVIDENCE)
        cls.editorial=read(EDITORIAL)
        cls.history=read(HISTORY)
        cls.allowed=read(SOURCE_ALLOWLIST)["urls"]
    def test_six_approved_new_works_generate_exact_19_official_recite(self):
        # This test must pass both before the first autonomous publication
        # and after the catalog has grown: immutable work IDs are not reset.
        expected={
            "La straniera":2,"Il ritorno di Ulisse in patria":4,
            "Vanessa":3,"I due Foscari":2,"Tristan und Isolde":5,"Accabadora":3}
        registered={x["title"] for x in self.registry["works"].values()}
        remaining={title:count for title,count in expected.items()
                   if title not in registered}
        intelligence=official_identity_candidates(self.evidence,self.candidates,
                                                   {"schema_version":1,"works":[]})
        source=[x for x in intelligence["works"]
                if x["source_key"]=="bologna-comunale-opera-2027"]
        self.assertEqual({x["title"] for x in source},set(remaining))
        # This regression isolates Bologna, while the shared resolver now covers every source.
        bologna_intelligence={"schema_version":1,"works":source}
        result=promote_new_works(self.facts,self.registry,self.evidence,
             self.candidates,bologna_intelligence,self.editorial,self.allowed,
             today=date(2026,11,21),history=self.history)
        facts,registry,urls,editorial,history,report=result
        self.assertEqual(report["new_works"],len(remaining))
        self.assertEqual(report["new_stagings"],len(remaining))
        self.assertEqual(report["new_recite"],sum(remaining.values()))
        bologna=[x for x in facts["productions"] if x["municipality"]=="Bologna"]
        self.assertEqual(len(bologna),9)
        self.assertEqual(sum(len(x["dates"]) for x in bologna),38)
        manzoni=[p for p in bologna if p["venue"]=="Teatro Auditorium Manzoni"]
        self.assertEqual({p["title"] for p in manzoni},{"La straniera","I due Foscari"})
        self.assertEqual(sum(len(p["dates"]) for p in manzoni),4)
        self.assertEqual(dict(next(p for p in bologna if p["title"]==
                            "Il ritorno di Ulisse in patria")["dates"])["2027-03-07"],"16:00")
        accabadora=next(x for x in registry["works"].values()
                        if x["title"]=="Accabadora")
        self.assertEqual(accabadora["composer"],"Francesco Filidei")
        self.assertEqual(history["works"]["accabadora"]["premiere_year"],2026)
        self.assertEqual(history["works"]["accabadora"]["premiere_city"],"Aix-en-Provence")
        graph=assemble(facts,registry,approved_extra=set(urls))
        self.assertEqual(len(graph["works"]),len(self.registry["works"])+len(remaining))
        published=build_editorial(facts,registry,editorial,
                                  approved_extra=set(urls),history=history)
        self.assertEqual(len(published["works"]),len(graph["works"]))
        again=promote_new_works(facts,registry,self.evidence,
                self.candidates,bologna_intelligence,editorial,urls,
                today=date(2026,11,21),history=history)
        self.assertEqual(again[-1]["new_recite"],0)
        self.assertEqual(again[0],facts)
        self.assertEqual(again[1],registry)
    def test_unknown_source_or_mismatched_composer_cannot_be_seeded(self):
        import copy
        evidence=copy.deepcopy(self.evidence)
        sample=next(x for x in evidence["evidence"]
                    if x.get("source_url","").endswith("/accabadora-2027/"))
        sample["event_facts"][0]["composer"]="Unrelated Composer"
        import copy as copy_module
        scan=copy_module.deepcopy(self.candidates)
        for candidate in scan["candidates"]:
            if candidate.get("official_url")==sample["source_url"]:
                candidate["status"]="needs_review"
        candidates=official_identity_candidates(
            evidence,scan,{"schema_version":1,"works":[]})
        self.assertFalse(any(x["source_url"]==sample["source_url"]
                             for x in candidates["works"]))

if __name__=="__main__":unittest.main()
