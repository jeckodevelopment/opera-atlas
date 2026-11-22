"""Messina 2026/27 stays exact; future category pages remain review-only."""
import copy
import json
import unittest
from datetime import date
from scripts.discover_season_indexes import CONFIG,extract,validate_config
from scripts.rollover_season_indexes import next_index

KEY="messina-vittorio-opera-2026-27"
HOST="https://www.teatrovittorioemanuele.it"
FUTURE=HOST+"/event_listing_type/opera-27-28/"

class MessinaFutureSeasons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
        cls.current=next(x for x in cls.config["sources"] if x["key"]==KEY)

    def test_future_url_rolls_year_after_year(self):
        self.assertIsNone(next_index(self.current,today=date(2026,11,22)))
        self.assertEqual(next_index(self.current,today=date(2026,11,22),
                                    allow_early=True),FUTURE)
        self.assertEqual(next_index(self.current,today=date(2027,6,1)),FUTURE)
        follow=dict(self.current,url=FUTURE)
        self.assertEqual(next_index(follow,today=date(2028,6,1)),
                         HOST+"/event_listing_type/opera-28-29/")
        self.assertIsNone(next_index(dict(self.current,url=HOST+
                    "/event_listing_type/opera-27-29/"),today=date(2028,6,1),
                    allow_early=True))

    def test_future_season_requires_explicit_heading_and_official_links(self):
        html='<h1>Tipo di evento: Opera 27/28</h1><h2>Spettacoli</h2>'
        html+=''.join(f'<a href="/evento/nuova-opera-{i}/">Opera</a>' for i in range(3))
        html+='<a href="https://example.org/evento/fake/">External</a>'
        html+='<a href="/evento/with-query/?ref=1">Tracking</a>'
        self.assertEqual(extract(KEY,FUTURE,html,3),
                         [HOST+f"/evento/nuova-opera-{i}/" for i in range(3)])
        for wrong in (html.replace("Opera 27/28","Prosa 27/28"),
                      html.replace("Opera 27/28","Opera 26/27")):
            with self.assertRaises(ValueError):
                extract(KEY,FUTURE,wrong,3)
        with self.assertRaises(ValueError):
            extract(KEY,FUTURE,html.replace("nuova-opera-2","nuova-opera-1"),3)

    def test_future_index_is_accepted_only_on_exact_official_host(self):
        next_config=copy.deepcopy(self.config)
        item=next(x for x in next_config["sources"] if x["key"]==KEY)
        item["url"]=FUTURE
        validate_config(next_config)
        for bad in (HOST+"/event_listing_type/opera-27-29/",
                    HOST+"/event_listing_type/opera-27-28/?filter=opera",
                    "https://other.example/event_listing_type/opera-27-28/"):
            item["url"]=bad
            with self.assertRaises(ValueError):
                validate_config(next_config)

if __name__=="__main__":
    unittest.main()
