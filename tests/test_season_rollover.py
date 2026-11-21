"""Rollover requires new official season and complete, approved index."""
import copy
import json
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.discover_season_indexes import CONFIG,validate_config,eligible
from scripts.rollover_season_indexes import next_index,roll

class SeasonRolloverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_upcoming_seasons_are_derived_from_fixed_official_hosts(self):
        items={x["key"]:x for x in self.config["sources"]}
        self.assertIsNone(next_index(items["scala-season-2026-27"],
                                     today=date(2027,5,31)))
        self.assertEqual(next_index(items["scala-season-2026-27"],
                                    today=date(2027,6,1)),
                         "https://www.teatroallascala.org/it/stagione/2027-2028/index.html")
        self.assertEqual(next_index(items["fenice-opera-2026-27"],
                                    today=date(2027,6,1)),
                         "https://www.teatrolafenice.it/event-category/opera-2027-28/")
        self.assertEqual(next_index(items["massimo-season-2026-27"],
                                    today=date(2027,6,1)),
                         "https://www.teatromassimo.it/la-stagione-2027-28/")
        self.assertIsNone(next_index(items["arena-festival-2027"],
                                     today=date(2027,6,1)))

    def test_complete_future_indexes_roll_forward_without_manual_edit(self):
        samples={
            "scala-season-2026-27":"".join(
                f'<a href="/it/stagione/2027-2028/opera/opera-{n}.html">Opera</a>'
                for n in range(3)),
            "fenice-opera-2026-27":
                '<a href="/event/some-future-opera/">Opera</a>'
                '<a href="/event/another-future-opera/">Opera</a>',
            "massimo-season-2026-27":
                '<h2>CALENDARIO OPERE E BALLETTI 2027-28</h2>'
                +''.join(f'<a href="/event/opera-future-{n}/">Opera</a>'
                         for n in range(6))
                +'<h2>CALENDARIO CONCERTI 2027-28</h2>',
        }
        def fetch(db,*,source_id,url,network_enabled):
            source=next(x for x in self.config["sources"]
                        if x["official_url"].split("/")[2]==url.split("/")[2])
            html=samples[source["key"]]
            return FetchResult(url,html,"a"*64,len(html))
        result,health=roll(self.config,today=date(2027,6,1),
                           network_enabled=True,fetcher=fetch)
        self.assertEqual(sum(x["status"]=="rolled" for x in health),3)
        self.assertEqual(len(result["sources"]),6)
        validate_config(result)
        scala=next(x for x in result["sources"] if x["key"]=="scala-season-2026-27")
        self.assertIn("2027-2028",scala["url"])
        self.assertTrue(eligible(scala["key"],
            "https://www.teatroallascala.org/it/stagione/2027-2028/opera/new-opera.html"))
        self.assertEqual(result["sources"][1],self.config["sources"][1])

    def test_blocked_or_incomplete_next_season_keeps_last_known_good(self):
        def deny(*args,**kwargs):raise FetchUnavailable("robots denied")
        result,status=roll(self.config,today=date(2027,6,1),
                           network_enabled=True,fetcher=deny)
        self.assertEqual(result,self.config)
        self.assertEqual(len(status),3)
        self.assertTrue(all(x["status"]=="kept_last_known_good" for x in status))
        def incomplete(db,*,source_id,url,network_enabled):
            html='<a href="/event/just-one/">One</a>'
            return FetchResult(url,html,"b"*64,len(html))
        result,status=roll(self.config,today=date(2027,6,1),
                           network_enabled=True,fetcher=incomplete)
        self.assertEqual(result,self.config)

    def test_bogus_season_path_not_approved(self):
        config=copy.deepcopy(self.config)
        config["sources"][0]["url"]="https://www.teatroallascala.org/it/stagione/2028-2027/index.html"
        with self.assertRaises(ValueError):
            validate_config(config)
        config=copy.deepcopy(self.config)
        config["sources"][2]["url"]="https://www.teatrolafenice.it/event-category/opera-2027-29/"
        with self.assertRaises(ValueError):
            validate_config(config)
if __name__=="__main__":
    unittest.main()
