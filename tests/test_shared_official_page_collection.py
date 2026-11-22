"""Batch acquisition reuses verified bytes, never candidate-specific parsing."""
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.collect_candidate_details import collect,selected_candidates

URL="https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2026/"
KEYS=(
 "jesi-don-pasquale-opera-2026",
 "jesi-nabucco-opera-2026",
 "jesi-esecuzione-opera-2026",
 "jesi-trittico-opera-2026",
)
def candidates():
    return {"schema_version":1,"candidates":[
      {"id":f"js-{i}","source_key":key,"official_url":URL,
       "status":"needs_review"}
      for i,key in enumerate(KEYS)]}

class SharedOfficialProgrammeFetchTests(unittest.TestCase):
    def test_same_page_is_fetched_once_but_evaluated_for_each_opera(self):
        seen=[]
        def fetch(db,*,source_id,url,network_enabled):
            seen.append((source_id,url))
            return FetchResult(url,"<h1>Test season</h1>", "a"*64,25)
        chosen=selected_candidates(candidates(),today=date(2026,11,22))
        self.assertEqual(len(chosen),4)
        evidence,health=collect(candidates(),{"schema_version":1,"evidence":[]},
            network_enabled=True,fetcher=fetch,today=date(2026,11,22))
        self.assertEqual(len(seen),1)
        self.assertEqual(len(health),4)
        self.assertEqual({x["candidate_id"] for x in health},
                         {x["id"] for x in candidates()["candidates"]})
        self.assertTrue(all(x["outcome"]=="unavailable_or_unstructured"
                            for x in health))
        self.assertEqual(evidence["evidence"],[])

    def test_failed_robots_gated_fetch_is_not_cached(self):
        attempts=[]
        def fetch(db,*,source_id,url,network_enabled):
            attempts.append(url)
            if len(attempts)==1:
                raise FetchUnavailable("official source unavailable")
            return FetchResult(url,"<h1>Incomplete</h1>","b"*64,24)
        _,health=collect(candidates(),{"schema_version":1,"evidence":[]},
             network_enabled=True,fetcher=fetch,today=date(2026,11,22))
        self.assertEqual(len(attempts),2)
        self.assertEqual(len(health),4)
        self.assertTrue(all(x["outcome"]=="unavailable_or_unstructured"
                            for x in health))

    def test_two_distinct_urls_never_share_evidence(self):
        selected=candidates()
        selected["candidates"]=selected["candidates"][:2]
        selected["candidates"][1]["official_url"]=(
          "https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2026/altro/")
        # Unsupported lookalike URLs are rejected by the source allowlist
        # instead of silently borrowing the approved shared page.
        chosen=selected_candidates(selected,today=date(2026,11,22))
        self.assertTrue(all(x["official_url"]==URL for x in chosen))

if __name__=="__main__":
    unittest.main()
