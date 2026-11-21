"""Three verified Rome 2027 operas are complete before first publication."""
import json
import unittest
from datetime import date

from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY,build_editorial,validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.auto_work_research import OUT as INTELLIGENCE

SOURCE="opera-roma-season-2026-27"
EXPECTED={
 "andrea-chenier":("Andrea Chénier","Umberto Giordano",7),
 "iphigenie-en-tauride":("Iphigénie en Tauride","Christoph Willibald Gluck",5),
 "il-trovatore":("Il trovatore","Giuseppe Verdi",7),
}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class RomeThreeCardsTests(unittest.TestCase):
    def test_official_identity_plot_history_and_licensed_historical_art(self):
        seeds=read(ROOT/"data/verified-work-authority-seeds.json")["works"]
        art=load_archival_art(set(EXPECTED))
        evidence=read(EVIDENCE)["evidence"]
        for slug,(title,composer,n) in EXPECTED.items():
            with self.subTest(slug=slug):
                rows=[x for x in seeds if x.get("source_key")==SOURCE and
                      x["source_url"].split("/")[-2] in (
                      "andrea-chenier-3","iphigenie-en-tauride","il-trovatore-3")
                      and x["title"]==title]
                self.assertEqual(len(rows),1)
                item=rows[0]
                self.assertEqual(item["composer"],composer)
                self.assertTrue(validate_history(item["history"]))
                self.assertTrue(45<=len(item["synopsis"])<=300)
                facts=[x for x in evidence if x["source_url"]==item["source_url"]]
                self.assertEqual(len(facts),1)
                self.assertEqual(len(facts[0]["event_facts"]),n)
                self.assertEqual({(x["event_title"],x["composer"]) for x in facts[0]["event_facts"]},
                                 {(title,composer)})
                self.assertEqual(art[slug]["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org",art[slug]["source_url"])

    def test_all_three_promote_through_common_work_graph_without_duplicates(self):
        registry=read(REGISTRY)
        facts=read(MANIFEST)
        editorial=read(EDITORIAL)
        history=read(HISTORY)
        candidates=read(CANDIDATES)
        evidence=read(EVIDENCE)
        intelligence=official_identity_candidates(
            evidence,candidates,read(INTELLIGENCE))
        chosen={"schema_version":1,"works":[w for w in intelligence["works"]
                 if w.get("source_key")==SOURCE and
                 w.get("source_url","").split("/")[-2] in (
                  "andrea-chenier-3","iphigenie-en-tauride","il-trovatore-3")]}
        previous={(normalized(w["title"]),normalized(w["composer"]))
                  for w in registry["works"].values()}
        remaining=[(t,c,n) for t,c,n in EXPECTED.values()
                   if (normalized(t),normalized(c)) not in previous]
        # Once these works are published, the official source records may
        # remain in the evidence queue until reconciliation. Publication must
        # be idempotent, not require the original queue to become empty.
        self.assertGreaterEqual(len(chosen["works"]),len(remaining))
        urls=read(SOURCE_ALLOWLIST)["urls"]
        result=promote_new_works(facts,registry,evidence,candidates,chosen,
                                 editorial,urls,today=date(2026,11,21),
                                 history=history,require_image=True)
        new_facts,new_registry,approved,new_editorial,new_history,report=result
        self.assertEqual(report["new_works"],len(remaining),report)
        self.assertEqual(report["new_recite"],sum(n for _,_,n in remaining),report)
        public=build_editorial(new_facts,new_registry,new_editorial,
                              approved_extra=set(approved),history=new_history)
        for title,composer,n in EXPECTED.values():
            self.assertEqual(len([w for w in public["works"]
                       if normalized(w["title"])==normalized(title) and
                       normalized(w["composer"])==normalized(composer)]),1)
            shows=[p for p in new_facts["productions"] if
                   p["municipality"]=="Roma" and
                   normalized(p["title"])==normalized(title)]
            self.assertEqual(len(shows),1)
            self.assertEqual(len(shows[0]["dates"]),n)
        again=promote_new_works(new_facts,new_registry,evidence,candidates,chosen,
                                new_editorial,approved,today=date(2026,11,21),
                                history=new_history,require_image=True)
        self.assertEqual(again[-1]["new_works"],0)
        self.assertEqual(again[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()
