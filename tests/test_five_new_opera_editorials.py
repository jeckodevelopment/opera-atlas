"""Five official opera candidates with formerly missing plots and archival art."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.auto_work_research import OUT as RESEARCH
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized,slugify
from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
from scripts.publish_work_posters import load_archival_art

EXPECTED={
    "https://www.teatroverdi-trieste.com/it/spettacoli/lohengrin/":
      ("Lohengrin","Richard Wagner",6),
    "https://www.liricocagliari.it/evento/don-carlos/":
      ("Don Carlos","Giuseppe Verdi",5),
    "https://www.liricocagliari.it/evento/alcina/":
      ("Alcina","Georg Friedrich Händel",5),
    "https://www.liricocagliari.it/evento/maria-stuarda/":
      ("Maria Stuarda","Gaetano Donizetti",5),
    "https://www.operaroma.it/spettacoli/la-cenerentola-3/":
      ("La Cenerentola","Gioachino Rossini",5),
}
SLUGS={"lohengrin","don-carlos","alcina","maria-stuarda","la-cenerentola"}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class CompleteFiveEditorials(unittest.TestCase):
    def test_scholarly_identity_and_poster_provenance(self):
        seeds={x["source_url"]:x for x in read(
            ROOT/"data/verified-work-authority-seeds.json")["works"]}
        observations={x["source_url"]:x for x in read(DETAILS)["evidence"]
                      if x.get("status")=="needs_editorial_review"}
        for url,(title,composer,count) in EXPECTED.items():
            with self.subTest(url=url):
                source=seeds[url]
                rows=observations[url]["event_facts"]
                self.assertEqual((source["title"],source["composer"]),(title,composer))
                self.assertEqual({(x["event_title"],x["composer"]) for x in rows},
                                 {(title,composer)})
                self.assertEqual(len(rows),count)
                self.assertTrue(validate_history(source["history"]))
                self.assertTrue(45<=len(source["synopsis"])<=300)
        images=load_archival_art(SLUGS)
        self.assertEqual(set(images),SLUGS)
        for poster in images.values():
            self.assertEqual(poster["kind"],"archival_work_image")
            self.assertIn("commons.wikimedia.org",poster["source_url"])

    def test_published_new_work_candidates_not_marked_for_review(self):
        queue=read(CANDIDATES)["candidates"]
        manifest=read(MANIFEST)["productions"]
        published={x["source_url"] for x in manifest}
        by_url={x["official_url"]:x["status"] for x in queue}
        for url in EXPECTED:
            with self.subTest(url=url):
                if url in published:
                    self.assertEqual(by_url[url],"already_catalogued")

    def test_autonomous_promotion_is_atomic_and_replay_safe(self):
        facts,registry=read(MANIFEST),read(REGISTRY)
        candidates,evidence=read(CANDIDATES),read(DETAILS)
        intelligence=official_identity_candidates(evidence,candidates,read(RESEARCH))
        selected={"schema_version":1,"works":[x for x in intelligence["works"]
                  if x.get("source_url") in EXPECTED]}
        previous={(normalized(x["title"]),normalized(x["composer"]))
                  for x in registry["works"].values()}
        remaining={url:v for url,v in EXPECTED.items()
                   if (normalized(v[0]),normalized(v[1])) not in previous}
        if not remaining:return
        self.assertEqual({x["source_url"] for x in selected["works"]
                          if x["source_url"] in remaining},set(remaining))
        editorial,history=read(EDITORIAL),read(HISTORY)
        urls=read(SOURCE_ALLOWLIST)["urls"]
        after=promote_new_works(facts,registry,evidence,candidates,selected,
                                editorial,urls,today=date(2026,11,21),
                                history=history,require_image=True)
        new_facts,new_registry,approved,new_ed,new_hist,report=after
        self.assertEqual(report["new_works"],len(remaining),report)
        self.assertEqual(report["new_recite"],
                         sum(v[2] for v in remaining.values()),report)
        for url,(title,composer,count) in remaining.items():
            matched=[p for p in new_facts["productions"]
                     if p["source_url"]==url
                     and normalized(p["title"])==normalized(title)
                     and normalized(p["composer"])==normalized(composer)]
            self.assertEqual(len(matched),1)
            self.assertEqual(len(matched[0]["dates"]),count)
            slug=slugify(title)
            self.assertIn(slug,new_ed["synopses"])
            self.assertTrue(validate_history(new_hist["works"][slug]))
        second=promote_new_works(new_facts,new_registry,evidence,candidates,
                                 selected,new_ed,approved,today=date(2026,11,21),
                                 history=new_hist,require_image=True)
        self.assertEqual(second[-1]["new_works"],0)
        self.assertEqual(second[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()
