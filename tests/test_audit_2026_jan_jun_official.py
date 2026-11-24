"""First-half 2026 historical scan remains bounded and official-source-scoped."""
import unittest
from unittest.mock import patch

from scripts.audit_2026_jan_jun_official import detail_links, scan, validate_seeds, credited_official_opera_facts


class HistoricalJanJunTests(unittest.TestCase):
    def test_links_discovered_from_official_site_only(self):
        html = ('<a href="/event/la-clemenza-di-tito/">La clemenza di Tito</a>'
                '<a href="https://other.example/event/carmen/">Carmen</a>'
                '<a href="/privacy/">Privacy</a>')
        self.assertEqual(
            ["https://www.teatrolafenice.it/event/la-clemenza-di-tito/"],
            detail_links(html,"https://www.teatrolafenice.it/event-category/opera-2025-26/",
                         "https://www.teatrolafenice.it/"))

    def test_already_reviewed_historical_regio_host_is_source_scoped(self):
        s={"key":"regio-2025-26","venue_id":"v1","city":"Torino",
           "season":"2025/26","official_url":"https://www.teatroregio.torino.it/",
           "url":"https://www.teatroregio.torino.it/stagione25-26"}
        historical={"records":[{"venue_id":"v1","city":"Torino",
                   "source_type":"official_event_detail","audience":"general_public",
                   "source_url":"https://www.teatroregio.torino.it/opera-e-balletto-2025-2026/macbeth",
                   "dates":[{"date":"2026-02-24","time":"19:00"}]}]}
        directory={"venues":[{"id":"v1","name":"Regio","city":"Torino"},
                             {"id":"v2","name":"Other","city":"Milano"}]}
        with patch('scripts.audit_2026_jan_jun_official.validate_config',
                   return_value=[]):
            self.assertEqual([s],validate_seeds({"schema_version":1,"year":2026,"seeds":[s]},
                                                 {},directory,historical))
            hostile={**s,"venue_id":"v2","city":"Milano"}
            with self.assertRaises(ValueError):
                validate_seeds({"schema_version":1,"year":2026,"seeds":[hostile]},
                               {},directory,historical)
            wrong={**s,"official_url":"https://other.example/",
                   "url":"https://other.example/archive"}
            with self.assertRaises(ValueError):
                validate_seeds({"schema_version":1,"year":2026,"seeds":[wrong]},
                               {},directory,historical)

    def test_scala_official_2025_26_credit_and_exact_2026_showtime(self):
        html=('<p>Opera</p><h1>Macbeth</h1><p>Giuseppe Verdi</p>'
              '<p>Dal 12 marzo 2026</p><div>12 marzo 2026 Ore 20:00</div>')
        facts=credited_official_opera_facts(
            html,"https://www.teatroallascala.org/it/stagione/2025-2026/opera/macbeth.html")
        self.assertEqual(1,len(facts))
        self.assertEqual("2026-03-12",facts[0]["date"])
        self.assertEqual("20:00",facts[0]["starts_at"][11:16])
        self.assertEqual("Giuseppe Verdi",facts[0]["composer"])

    def test_unapproved_scala_year_never_parsed(self):
        html='<h1>Macbeth</h1>'
        self.assertEqual([],credited_official_opera_facts(
            html,"https://www.teatroallascala.org/it/stagione/2024-2025/opera/macbeth.html"))

    def test_no_network_error_never_certifies_complete(self):
        source={"key":"fenice-2025-26","venue_id":"v1","city":"Venezia",
                "season":"2025/26","official_url":"https://www.teatrolafenice.it/",
                "url":"https://www.teatrolafenice.it/event-category/opera-2025-26/"}
        config={"schema_version":1,"sources":[]}
        directory={"venues":[{"id":"v1","name":"Fenice","city":"Venezia"}]}
        from opera_atlas.controlled_fetch import AccessDenied
        def denied(*args):
            raise AccessDenied("robots")
        with patch('scripts.audit_2026_jan_jun_official.validate_config',
                   return_value=[{"official_url":source["official_url"],
                                  "access_status":"approved"}]):
            result=scan({"schema_version":1,"year":2026,"seeds":[source]},
                        config,directory,fetch_page=denied,workers=1)
        self.assertEqual(0,result["complete_seasons_certified"])
        self.assertEqual(0,result["seed_pages_acquired"])
        self.assertEqual([],result["observations"])
        self.assertFalse(result["catalog_updated"])

    def test_index_with_event_facts_is_restricted_to_first_half(self):
        source={"key":"fenice-2025-26","venue_id":"v1","city":"Venezia",
                "season":"2025/26","official_url":"https://www.teatrolafenice.it/",
                "url":"https://www.teatrolafenice.it/event-category/opera-2025-26/"}
        config={"schema_version":1,"sources":[]}
        directory={"venues":[{"id":"v1","name":"Fenice","city":"Venezia"}]}
        def fake(*args):
            return ('<script type="application/ld+json">'
                    '{"@context":"https://schema.org","@type":"Event",'
                    '"name":"Example","startDate":"2026-03-02T20:00:00+01:00"}</script>')
        with patch('scripts.audit_2026_jan_jun_official.validate_config',
                   return_value=[{"official_url":source["official_url"],
                                  "access_status":"approved"}]):
            result=scan({"schema_version":1,"year":2026,"seeds":[source]},
                        config,directory,fetch_page=fake,workers=1)
        self.assertTrue(result["read_only"])
        self.assertEqual(0,result["complete_seasons_certified"])


if __name__=="__main__":
    unittest.main()
