"""Multi-year Carlo Felice and early Piacenza discovery regression checks."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable
from scripts.discover_season_indexes import CONFIG, eligible, validate_config
from scripts.rollover_season_indexes import next_index, roll


class FutureSeasonRollovers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.sources={row["key"]:row for row in cls.config["sources"]}

    def test_carlo_felice_early_and_consecutive_seasons(self):
        item=self.sources["carlo-felice-season-2026-27"]
        expected="https://www.carlofelice.it/rassegna-stagione-opera-danza-musical-2027-28/"
        self.assertIsNone(next_index(item,today=date(2026,11,22)))
        self.assertEqual(next_index(item,today=date(2026,11,22),
                                    allow_early=True),expected)
        self.assertEqual(next_index(item,today=date(2027,6,1)),expected)
        following=dict(item,url=expected)
        self.assertEqual(next_index(following,today=date(2028,6,1)),
            "https://www.carlofelice.it/rassegna-stagione-opera-danza-musical-2028-29/")
        self.assertIsNone(next_index(dict(item,url=expected.replace("2027-28","2027-29")),
                                     today=date(2028,6,1),allow_early=True))
        future=copy.deepcopy(self.config)
        for row in future["sources"]:
            if row["key"]==item["key"]:
                row["url"]=expected
        validate_config(future)
        self.assertTrue(eligible(item["key"],"https://www.carlofelice.it/spettacolo/example/"))

    def test_piacenza_next_season_discovered_before_prior_season_end(self):
        item=self.sources["piacenza-opera-2026-27"]
        self.assertEqual(next_index(item,today=date(2026,11,22),
                                    allow_early=True),
                         "https://teatripiacenza.it/stagioni/stagione-27-28/")
        self.assertIsNone(next_index(item,today=date(2026,11,22)))

    def test_verified_index_rolls_without_changing_other_sources(self):
        item=self.sources["carlo-felice-season-2026-27"]
        html="".join(f'<a href="/spettacolo/new-opera-{i}/">Opera</a>'
                     for i in range(item["min_links"]))
        def fetch(db,*,source_id,url,network_enabled):
            if "carlofelice.it" in url:
                return FetchResult(url,html,"a"*64,len(html))
            raise FetchUnavailable("page unavailable")
        changed,health=roll(self.config,today=date(2027,6,1),
                             network_enabled=True,fetcher=fetch)
        new=next(row for row in changed["sources"] if row["key"]==item["key"])
        self.assertIn("2027-28",new["url"])
        self.assertEqual(len(changed["sources"]),len(self.config["sources"]))
        self.assertEqual(next(row for row in health if row["key"]==item["key"])["status"],
                         "rolled")
        self.assertEqual(next(row for row in changed["sources"]
                              if row["key"]=="piacenza-opera-2026-27")["url"],
                         self.sources["piacenza-opera-2026-27"]["url"])

    def test_incomplete_future_index_keeps_last_known_good(self):
        def incomplete(db,*,source_id,url,network_enabled):
            html='<a href="/spettacolo/one/">Opera</a>'
            return FetchResult(url,html,"a"*64,len(html))
        changed,health=roll(self.config,today=date(2027,6,1),
                             network_enabled=True,fetcher=incomplete)
        self.assertEqual(changed,self.config)
        row=next(x for x in health if x["key"]=="carlo-felice-season-2026-27")
        self.assertEqual(row["status"],"kept_last_known_good")


if __name__=="__main__":
    unittest.main()
