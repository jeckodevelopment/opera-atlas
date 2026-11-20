"""Season indexes must discover only exact official URLs and preserve canon."""
import copy
import json
import unittest
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.discover_season_indexes import CONFIG,extract,scan

class NationalIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))
    def test_scala_only_opera_detail_links(self):
        url="https://www.teatroallascala.org/it/stagione/2026-2027/index.html"
        html='<a href="/it/stagione/2026-2027/opera/otello.html">Otello</a>'+\
            '<a href="/it/stagione/2026-2027/opera/don-giovanni.html">Don Giovanni</a>'+\
            '<a href="/it/stagione/2026-2027/opera/anna-bolena.html">Anna Bolena</a>'+\
            '<a href="/it/stagione/2026-2027/balletto/giselle.html">Giselle</a>'+\
            '<a href="https://external.example/it/stagione/2026-2027/opera/fake.html">Fake</a>'
        links=extract("scala-season-2026-27",url,html,3)
        self.assertEqual(len(links),3)
        self.assertTrue(all("/opera/" in x for x in links))
    def test_arena_and_fenice_index_filter(self):
        arena="https://www.arena.it/arena-opera-festival/spettacoli/"
        a=extract("arena-festival-2027",arena,
                  '<a href="/arena-opera-festival/nabucco/">Nabucco</a>'
                  '<a href="/arena-opera-festival/carmen/">Carmen</a>'
                  '<a href="/arena-opera-festival/calendario/">Calendario</a>',2)
        self.assertEqual(len(a),2)
        fenice="https://www.teatrolafenice.it/event-category/opera-2026-27/"
        f=extract("fenice-opera-2026-27",fenice,
                  '<a href="/event/jenufa/">Jenufa</a>'
                  '<a href="/event/fedora/">Fedora</a>'
                  '<a href="/news/other/">News</a>',2)
        self.assertEqual(len(f),2)
    def test_incomplete_index_is_rejected(self):
        with self.assertRaises(ValueError):
            extract("scala-season-2026-27",
                    "https://www.teatroallascala.org/it/stagione/2026-2027/index.html",
                    "<a href='/it/stagione/2026-2027/opera/otello.html'>Otello</a>",3)
    def test_scans_are_idempotent_and_never_publish_events(self):
        htmls={
          "scala-season-2026-27":'<a href="/it/stagione/2026-2027/opera/otello.html">Otello</a>'
            '<a href="/it/stagione/2026-2027/opera/don-giovanni.html">Don Giovanni</a>'
            '<a href="/it/stagione/2026-2027/opera/anna-bolena.html">Anna Bolena</a>',
          "arena-festival-2027":'<a href="/arena-opera-festival/nabucco/">Nabucco</a>'
            '<a href="/arena-opera-festival/carmen/">Carmen</a>',
          "fenice-opera-2026-27":'<a href="/event/jenufa/">Jenufa</a><a href="/event/fedora/">Fedora</a>'
        }
        def fake(db,*,source_id,url,network_enabled):
            key=next(x["key"] for x in self.config["sources"] if x["url"]==url)
            html=htmls[key]
            return FetchResult(url,html,"a"*64,len(html))
        empty={"schema_version":1,"candidates":[]}
        first,status=scan(self.config,empty,fetcher=fake,network_enabled=True,
                          now="2026-11-20T20:00:00+00:00")
        self.assertEqual(len(first["candidates"]),7)
        self.assertTrue(all(x["status"]=="needs_review" for x in first["candidates"]))
        self.assertTrue(all("date" not in x and "composer" not in x for x in first["candidates"]))
        second,_=scan(self.config,first,fetcher=fake,network_enabled=True,
                       now="2026-11-20T20:00:00+00:00")
        self.assertEqual(second,first)
        self.assertTrue(all(x["status"]=="success" for x in status))
    def test_access_and_robots_failure_preserve_last_good(self):
        source=copy.deepcopy(self.config)
        source["sources"][0]["access_status"]="blocked"
        def deny(*args,**kwargs):raise FetchUnavailable("robots unavailable")
        existing={"schema_version":1,"candidates":[]}
        data,health=scan(source,existing,fetcher=deny,network_enabled=True,
                         now="2026-11-20T20:00:00+00:00")
        self.assertEqual(data,existing)
        self.assertEqual(health[0]["status"],"blocked")
        self.assertEqual(health[1]["status"],"unavailable_or_invalid")

if __name__=="__main__":
    unittest.main()
