"""Source onboarding probe must never alter catalog, IDs or access status."""
import json
import unittest
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.probe_pending_sources import evaluate
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import CONFIG

class ReadOnlyProbeTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.before=json.dumps((self.config,self.facts),sort_keys=True)
        self.sources=[s for s in self.config["sources"] if s["adapter"] in ("scala","arena")]
        self.assertEqual(len(self.sources),3)

    def test_robots_unavailable_never_writes_catalog(self):
        def blocked(*args,**kwargs):
            raise FetchUnavailable("robots unavailable")
        reports=evaluate(self.config,self.facts,fetcher=blocked)["reports"]
        self.assertEqual(len(reports),3)
        self.assertTrue(all(s["status"]=="not_verified" for s in reports))
        self.assertEqual(json.dumps((self.config,self.facts),sort_keys=True),self.before)

    def test_wrong_or_unparseable_page_never_marks_verified(self):
        def page(*args,**kwargs):
            return FetchResult(kwargs["url"],"<html>Page temporarily unavailable</html>","a"*64,40)
        reports=evaluate(self.config,self.facts,fetcher=page)["reports"]
        self.assertTrue(all(s["status"]=="not_verified" for s in reports))

    def test_registry_block_prevents_any_request(self):
        for src in self.sources:
            src["access_status"]="blocked"
        def fail(*args,**kwargs):
            raise AssertionError("blocked source should not fetch")
        result=evaluate(self.config,self.facts,fetcher=fail)
        self.assertEqual({r["status"] for r in result["reports"]},{"blocked_by_registry"})

if __name__=="__main__":
    unittest.main()
