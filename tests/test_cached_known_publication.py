"""Fast cached acquisition must publish known verified Genova dates offline."""
import json
import unittest
from datetime import date
from scripts.publish_cached_known import prepare
from scripts.build_verified_catalog import MANIFEST,TIME_EVIDENCE
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.auto_catalogue import SOURCE_ALLOWLIST

class CachedKnownPublicationTests(unittest.TestCase):
    def test_all_11_source_verified_lucca_and_sassari_recite_publish_offline(self):
        from scripts.auto_catalogue import promote
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        selected={"giglio-lucca-opera-2026-27","sassari-de-carolis-opera-2026"}
        wanted=lambda x:x["source_key"] in selected and (
            x["source_key"]=="sassari-de-carolis-opera-2026" or
            not x["official_url"].endswith("/lanno-che-verra/"))
        chosen=[{**x,"status":"needs_review"} for x in candidates["candidates"]
                if wanted(x)]
        details=[x for x in evidence["evidence"] if wanted({
            "source_key":x["source_key"],"official_url":x["source_url"]})]
        self.assertEqual(len(chosen),6)
        self.assertEqual(len(details),6)
        result,ids,urls,report=promote(
            facts,registry,{"schema_version":1,"evidence":details},
            {"schema_version":1,"candidates":chosen},[],today=date(2026,11,22))
        sources={x["official_url"] for x in chosen}
        staged=[p for p in result["productions"] if p["source_url"] in sources]
        self.assertEqual(len(staged),6,report)
        self.assertEqual(sum(len(p["dates"]) for p in staged),11,report)
        self.assertEqual({p["municipality"] for p in staged},{"Lucca","Sassari"})
        self.assertIn("https://www.marialisadecarolis.it/opera-lirica.aspx?id=373",urls)
        again,again_ids,_,second=promote(result,ids,
            {"schema_version":1,"evidence":details},
            {"schema_version":1,"candidates":chosen},urls,today=date(2026,11,22))
        self.assertEqual(second["new_recite"],0)
        self.assertEqual(again,result)
        self.assertEqual(again_ids,ids)

    def test_four_genova_productions_publish_offline_without_new_work_id(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        urls=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        times=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        # Identify the exact offending source when approved index URL rules
        # evolve independently of a previously verified cached feed.
        from scripts.build_verified_catalog import validate_auto_sources
        for source_url in urls:
            with self.subTest(source_url=source_url):
                validate_auto_sources([source_url])
        result,ids,approved,new_times,report=prepare(
            facts,registry,evidence,candidates,urls,times,today=date(2026,11,21))
        # Other officially verified backlog items (such as Don Pasquale at
        # Jesi) can promote a pre-reserved identity in this same offline pass.
        # No *new* identity may be allocated by the cached-known path.
        old={v["id"] for name in ("works","reserved_works")
             for v in registry.get(name,{}).values()}
        new={v["id"] for name in ("works","reserved_works")
             for v in ids.get(name,{}).values()}
        self.assertEqual(old,new)
        self.assertEqual({k:v for k,v in ids["works"].items()
                          if k in registry["works"]},registry["works"])
        genova=[p for p in result["productions"] if p["municipality"]=="Genova"]
        self.assertGreaterEqual(len(genova),4,report)
        self.assertGreaterEqual(sum(len(p["dates"]) for p in genova),24,report)
        self.assertTrue(all(p["venue"]=="Teatro Carlo Felice" for p in genova))
        self.assertTrue(all(p["source_url"] in approved for p in genova))
        public=assemble(result,ids,approved_extra=set(approved))
        self.assertTrue(public["performances"])
        again,again_ids,again_urls,again_times,second=prepare(
            result,ids,evidence,candidates,approved,new_times,today=date(2026,11,21))
        self.assertEqual(second["new_recite"],0,second)
        self.assertEqual(second["enriched_recite_times"],0,second)
        self.assertEqual(again,result)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,approved)
        self.assertEqual(again_times,new_times)

if __name__=="__main__":
    unittest.main()
