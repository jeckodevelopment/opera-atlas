"""Three sourced editorial candidates must publish as complete work cards.

All inputs are the repository's official detail checkpoints: no web access,
API keys, fabricated events, or manual Joomla/site assertions.
"""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.auto_work_research import OUT as RESEARCH
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized,slugify
from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
from scripts.publish_work_posters import load_archival_art

EXPECTED={
    "https://teatroregioparma.it/spettacolo/la-clemenza-di-tito/":
        ("La clemenza di Tito","Wolfgang Amadeus Mozart",2),
    "https://www.teatrolafenice.it/event/larca-di-noe/":
        ("L'arca di Noè","Benjamin Britten",1),
    "https://www.operaroma.it/spettacoli/la-rondine/":
        ("La rondine","Giacomo Puccini",6),
}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class SourceVerifiedBlockedWorks(unittest.TestCase):
    def test_three_seeded_works_are_attributed_to_matching_official_evidence(self):
        seeds={w["source_url"]:w for w in read(
            ROOT/"data/verified-work-authority-seeds.json")["works"]}
        evidence={w["source_url"]:w for w in read(DETAILS)["evidence"]
                  if w.get("status")=="needs_editorial_review"}
        for url,(title,composer,count) in EXPECTED.items():
            with self.subTest(url=url):
                seed=seeds[url]
                facts=evidence[url]["event_facts"]
                self.assertEqual((seed["title"],seed["composer"]),(title,composer))
                self.assertEqual({(x["event_title"],x["composer"]) for x in facts},
                                 {(title,composer)})
                self.assertEqual(len(facts),count)
                self.assertTrue(validate_history(seed["history"]))
                self.assertTrue(45<=len(seed["synopsis"])<=300)
                self.assertFalse(seed["synopsis"].endswith(
                    "Consulta le rappresentazioni verificate in programma nei teatri italiani."))
                self.assertTrue(all(s.startswith("https://") for s in
                                    seed["history"]["sources"]))
        archival=load_archival_art({"la-clemenza-di-tito","la-rondine"})
        self.assertEqual(set(archival),{"la-clemenza-di-tito","la-rondine"})
        self.assertTrue(all("commons.wikimedia.org" in x["source_url"]
                            for x in archival.values()))

    def test_full_publication_transaction_of_three_complete_works(self):
        facts,registry=read(MANIFEST),read(REGISTRY)
        evidence,candidates=read(DETAILS),read(INDEX)
        editorial,history=read(EDITORIAL),read(HISTORY)
        intelligence=official_identity_candidates(evidence,candidates,read(RESEARCH))
        selected={"schema_version":1,"works":[entry for entry in intelligence["works"]
                  if entry.get("source_url") in EXPECTED]}
        already={(normalized(w["title"]),normalized(w["composer"]))
                 for w in registry["works"].values()}
        remaining={url:record for url,record in EXPECTED.items()
                   if (normalized(record[0]),normalized(record[1])) not in already}
        # After a successful scheduled refresh these rows are already
        # canonical and should not re-enter promotion as new works.
        if not remaining:
            self.assertEqual(remaining,{})
            return
        self.assertEqual({w["source_url"] for w in selected["works"]
                          if w["source_url"] in remaining},set(remaining))
        urls=read(SOURCE_ALLOWLIST)["urls"]
        result=promote_new_works(facts,registry,evidence,candidates,selected,
                                 editorial,urls,today=date(2026,11,21),
                                 history=history,require_image=True)
        new_facts,new_registry,approved,new_ed,new_hist,report=result
        self.assertEqual(report["new_works"],len(remaining),report)
        self.assertEqual(report["new_recite"],sum(v[2] for v in remaining.values()),report)
        for url,(title,composer,count) in remaining.items():
            matched=[p for p in new_facts["productions"]
                     if p["source_url"]==url and
                     normalized(p["title"])==normalized(title) and
                     normalized(p["composer"])==normalized(composer)]
            self.assertEqual(len(matched),1)
            self.assertEqual(len(matched[0]["dates"]),count)
            key=slugify(title)
            self.assertIn(key,new_ed["synopses"])
            self.assertTrue(validate_history(new_hist["works"][key]))
        replay=promote_new_works(new_facts,new_registry,evidence,candidates,
                                 selected,new_ed,approved,
                                 today=date(2026,11,21),history=new_hist,
                                 require_image=True)
        self.assertEqual(replay[-1]["new_works"],0)
        self.assertEqual(replay[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()
