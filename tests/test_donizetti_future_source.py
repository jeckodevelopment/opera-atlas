"""Future Donizetti editions have an independent year-scoped source."""
import copy
import json
import unittest
from datetime import date
from scripts.discover_season_indexes import CONFIG,extract,validate_config,eligible
from scripts.rollover_season_indexes import next_index
from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable
from scripts.discover_season_indexes import scan

KEY="donizetti-opera-2027"
OLD="donizetti-opera-2026"
HOST="https://www.donizettiopera.org"
CURRENT=HOST+"/it/opere-2027/"
FUTURE=HOST+"/it/opere-2028/"
def page(year):
    return (f'<h1>OPERE {year}</h1>'
      +''.join(f'<a href="/it/evento/nuova-opera-{i}/">Opera</a>' for i in range(3))
      +'<h1>EVENTI COLLATERALI</h1>'
      +'<a href="/it/evento/concerto-extra/">Concerto</a>'
      +'<footer><a href="/it/evento/archivio/">Archivio</a></footer>')

class DonizettiFutureSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
        cls.item=next(x for x in cls.config["sources"] if x["key"]==KEY)
        cls.old=next(x for x in cls.config["sources"] if x["key"]==OLD)

    def test_early_2028_and_following_years(self):
        self.assertIsNone(next_index(self.item,today=date(2027,8,31)))
        self.assertEqual(next_index(self.item,today=date(2026,11,22),
                                    allow_early=True),FUTURE)
        self.assertEqual(next_index(self.item,today=date(2027,9,1)),FUTURE)
        self.assertEqual(next_index(dict(self.item,url=FUTURE),
                                    today=date(2028,9,1)),
                         HOST+"/it/opere-2029/")
        amended=copy.deepcopy(self.config)
        next(x for x in amended["sources"] if x["key"]==KEY)["url"]=FUTURE
        validate_config(amended)

    def test_future_opera_scope_and_year_provenance(self):
        expected=[HOST+f"/it/evento/nuova-opera-{i}/" for i in range(3)]
        self.assertEqual(extract(KEY,CURRENT,page(2027),1),expected)
        self.assertEqual(extract(KEY,FUTURE,page(2028),1),expected)
        self.assertTrue(eligible(KEY,expected[0]))
        self.assertFalse(eligible(OLD,expected[0]))
        for wrong in (2026,2028):
            with self.subTest(year=wrong),self.assertRaises(ValueError):
                extract(KEY,CURRENT,page(wrong),1)
        with self.assertRaises(ValueError):
            extract(KEY,CURRENT,"<nav><a href='/it/evento/nuova-opera-0/'>"
                    "OPERE 2027</a></nav>",1)

    def test_2026_approved_sources_stay_exact(self):
        original=HOST+"/it/opere-2026/"
        links=['/it/evento/l-esule-di-roma/','/it/evento/alahor-in-granata/2026-11-14/',
               '/it/evento/le-convenienze-ed-inconvenienze-teatrali/']
        html='<h1>OPERE 2026</h1>'+''.join(f'<a href="{x}">Opera</a>' for x in links)
        self.assertEqual(extract(OLD,original,html,3),sorted(HOST+x for x in links))
        self.assertFalse(eligible(OLD,HOST+"/it/evento/nuova-opera-1/"))
        self.assertEqual(self.old["url"],original)

    def test_future_dated_archive_is_not_accepted(self):
        html='<h1>OPERE 2027</h1>'
        html+=''.join(f'<a href="/it/evento/nuova-opera-{i}/2027-11-1{i}/">Opera</a>' for i in range(3))
        html+='<a href="/it/evento/vecchia-opera/2026-11-10/">Archivio</a>'
        self.assertEqual(len(extract(KEY,CURRENT,html,1)),3)

    def test_unavailable_future_keeps_2027_source_and_2026_untouched(self):
        config=copy.deepcopy(self.config)
        for row in config["sources"]:
            if row["key"]!=KEY:row["access_status"]="blocked"
        def fetch(db,*,source_id,url,network_enabled):
            if "/opere-2028/" in url:raise FetchUnavailable("page unavailable")
            return FetchResult(url,page(2027),"a"*64,len(page(2027)))
        result,health=scan(config,{"schema_version":1,"candidates":[]},
                    network_enabled=True,check_next_season=True,fetcher=fetch)
        row=next(x for x in health if x["key"]==KEY)
        self.assertEqual(row["status"],"success")
        self.assertEqual(row["next_season_status"],"unavailable_or_invalid")
        self.assertEqual(len(result["candidates"]),3)

if __name__=="__main__":
    unittest.main()
