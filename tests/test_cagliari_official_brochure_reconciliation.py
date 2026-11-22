"""Finite first-party Cagliari 2027 brochure controls the global-index backlog."""
import json
import unittest
from scripts.reconcile_published_candidates import (
    verified_cagliari_2027_brochure_urls,reconcile)
from scripts.discover_season_indexes import OUTPUT
from scripts.publish_catalog_v2 import ROOT

KEY="lirico-cagliari-opera-2027"
BASE="https://www.liricocagliari.it/evento/"

class Cagliari2027FiniteSeason(unittest.TestCase):
    def test_verified_brochure_recognizes_seven_not_all_years_index(self):
        urls=verified_cagliari_2027_brochure_urls()
        self.assertEqual(len(urls),7)
        self.assertIn(BASE+"candide/",urls)
        self.assertNotIn(BASE+"norma/",urls)
        self.assertNotIn(BASE+"rigoletto/",urls)

    def test_reconcile_archives_seven_other_season_links_and_preserves_candide(self):
        urls=verified_cagliari_2027_brochure_urls()
        queue=json.loads(OUTPUT.read_text(encoding="utf-8"))
        from scripts.discover_season_indexes import reviewed_source_urls
        # Existing canonical URLs must always take precedence.
        published=reviewed_source_urls()
        reconciled,health=reconcile(
            queue,published,cagliari_season_urls=urls)
        per_url={x["official_url"]:x for x in reconciled["candidates"]}
        archived=[x for x in per_url.values()
                  if x["source_key"]==KEY and
                  x["status"]=="not_in_official_season"]
        self.assertGreaterEqual(len(archived),7)
        # The same first-party brochure supports the candidate both before
        # and after a concurrent verified publication. A known published URL
        # must become already_catalogued, not stay stuck in the review queue.
        candide_url=BASE+"candide/"
        expected="already_catalogued" if candide_url in published else "needs_review"
        self.assertEqual(per_url[candide_url]["status"],expected)
        # Other sources may be independently recatalogued by concurrent
        # publisher checkpoints: assert exact Cagliari statuses and local
        # idempotence, rather than global byte equality with an old snapshot.
        before={x["official_url"]:x for x in queue["candidates"] if x["source_key"]==KEY}
        after={x["official_url"]:x for x in reconciled["candidates"] if x["source_key"]==KEY}
        self.assertEqual(set(before),set(after))
        self.assertTrue(all(before[url]["first_seen"]==after[url]["first_seen"]
                            and before[url]["last_seen"]==after[url]["last_seen"]
                            for url in before))
        repeat,_=reconcile(reconciled,published,cagliari_season_urls=urls)
        self.assertEqual(repeat,reconciled)

    def test_official_brochure_can_restore_changed_season_or_canonical_work(self):
        url=BASE+"norma/"
        row={"id":"former","source_key":KEY,"official_url":url,
             "status":"not_in_official_season","first_seen":"fixture",
             "last_seen":"fixture"}
        queue={"schema_version":1,"candidates":[row]}
        removed,_=reconcile(queue,set(),cagliari_season_urls={BASE+"candide/"})
        self.assertEqual(removed["candidates"][0]["status"],"not_in_official_season")
        restored,_=reconcile(removed,set(),cagliari_season_urls={url})
        self.assertEqual(restored["candidates"][0]["status"],"needs_review")
        published,_=reconcile(removed,{url},cagliari_season_urls=set())
        self.assertEqual(published["candidates"][0]["status"],"already_catalogued")
        unknown,_=reconcile(removed,set())
        self.assertEqual(unknown["candidates"][0]["status"],"not_in_official_season")

    def test_no_untrusted_host_or_out_of_scope_source_retirement(self):
        row={"id":"other","source_key":"verdi-trieste-season-2026-27",
             "official_url":"https://www.teatroverdi-trieste.com/it/spettacoli/norma/",
             "status":"needs_review"}
        updated,_=reconcile({"schema_version":1,"candidates":[row]},set(),
                            cagliari_season_urls=set())
        self.assertEqual(updated["candidates"][0]["status"],"needs_review")

if __name__=="__main__":
    unittest.main()
