"""Current and next season are discovered without replacing the active index."""
import copy
import json
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable
from scripts.discover_season_indexes import CONFIG, scan
from scripts.rollover_season_indexes import next_index

class ParallelSeasonDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))

    def config_for_scala(self):
        config=copy.deepcopy(self.config)
        for item in config["sources"]:
            if item["key"]!="scala-season-2026-27":
                item["access_status"]="blocked"
        return config

    def html(self,year):
        return "".join(
            f'<a href="/it/stagione/{year}-{year+1}/opera/example-{i}.html">Opera</a>'
            for i in range(3))

    def test_next_season_can_be_checked_before_old_season_ends(self):
        item=next(x for x in self.config["sources"]
                  if x["key"]=="scala-season-2026-27")
        self.assertIsNone(next_index(item,today=date(2026,11,22)))
        self.assertEqual(next_index(item,today=date(2026,11,22),allow_early=True),
                         "https://www.teatroallascala.org/it/stagione/2027-2028/index.html")

    def test_two_season_candidates_are_preserved_without_rollover(self):
        config=self.config_for_scala()
        calls=[]
        def fetch(db,*,source_id,url,network_enabled):
            calls.append(url)
            year=2027 if "/2027-2028/" in url else 2026
            html=self.html(year)
            return FetchResult(url,html,"a"*64,len(html))
        result,rows=scan(config,{"schema_version":1,"candidates":[]},
                         fetcher=fetch,network_enabled=True,
                         check_next_season=True)
        scala=next(x for x in rows if x["key"]=="scala-season-2026-27")
        self.assertEqual(scala["status"],"success")
        self.assertEqual(scala["next_season_status"],"verified")
        self.assertEqual(scala["next_season_links"],3)
        self.assertEqual(scala["links"],6)
        self.assertEqual(len(calls),2)
        urls={x["official_url"] for x in result["candidates"]}
        self.assertEqual(len(urls),6)
        self.assertTrue(any("/2026-2027/" in x for x in urls))
        self.assertTrue(any("/2027-2028/" in x for x in urls))
        self.assertEqual(config["sources"][0]["url"],
                         self.config["sources"][0]["url"])

    def test_unavailable_future_keeps_current_candidates_and_health(self):
        config=self.config_for_scala()
        def fetch(db,*,source_id,url,network_enabled):
            if "/2027-2028/" in url:
                raise FetchUnavailable("page unavailable")
            html=self.html(2026)
            return FetchResult(url,html,"a"*64,len(html))
        result,rows=scan(config,{"schema_version":1,"candidates":[]},
                         fetcher=fetch,network_enabled=True,
                         check_next_season=True)
        scala=next(x for x in rows if x["key"]=="scala-season-2026-27")
        self.assertEqual(scala["status"],"success")
        self.assertEqual(scala["links"],3)
        self.assertEqual(scala["next_season_status"],"unavailable_or_invalid")
        self.assertEqual(len(result["candidates"]),3)

if __name__=="__main__":
    unittest.main()
