"""Exact two-work Trapani chamber programme must never become one hybrid opera."""
import unittest
from datetime import date

from opera_atlas.trapani_luglio_opera import (
    INDEX, parse_filidei_sciarrino_program)
from opera_atlas.controlled_fetch import FetchResult
from scripts.collect_candidate_details import collect

URL=(INDEX+
    "l-opera-forse-di-francesco-filidei-infinito-nero-di-salvatore-sciarrino/")

def page():
    return (
        "<h1>L'opera (forse) di Francesco Filidei / Infinito nero di Salvatore Sciarrino</h1>"
        "<p>Homepage Eventi Stagione 2026</p>"
        "<div>Opera da camera</div>"
        "<p>L'Opera (forse)</p><p>Musica di Francesco Filidei</p>"
        "<p>Libretto di Pierre Senges</p>"
        "<p>Infinito nero</p><p>Musica di Salvatore Sciarrino</p>"
        "<p>Libretto di Salvatore Sciarrino</p>"
        "<div>Teatro M° Tonino Pardo</div>"
        "<div>31 ottobre 2026, Ore 19:00</div>"
        "<h2>Personaggi e interpreti</h2>")

class TrapaniCompositeProgramme(unittest.TestCase):
    def test_two_distinct_works_share_one_physical_recita(self):
        title,components,venue,dates=parse_filidei_sciarrino_program(
            page(),url=URL)
        self.assertIn("Infinito nero",title)
        self.assertEqual(components,[
            {"title":"L'opera (forse)","composer":"Francesco Filidei"},
            {"title":"Infinito nero","composer":"Salvatore Sciarrino"}])
        self.assertEqual(venue,"Teatro M° Tonino Pardo")
        self.assertEqual(dates,[("2026-10-31","19:00")])

    def test_collector_never_creates_single_composer_hybrid(self):
        candidate={"schema_version":1,"candidates":[{
            "id":"test-trapani-composite",
            "source_key":"trapani-luglio-musicale-2026",
            "official_url":URL,"status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            self.assertEqual(url,URL)
            return FetchResult(url,page(),"b"*64,100)
        evidence,health=collect(
            candidate,{"schema_version":1,"evidence":[]},
            network_enabled=True,fetcher=fake,today=date(2026,11,23))
        self.assertEqual(health[0]["outcome"],"verified_composite_program",health)
        record=evidence["evidence"][0]
        self.assertEqual(record["status"],"needs_program_review")
        self.assertEqual(len(record["program_components"]),2)
        self.assertEqual(len(record["event_facts"]),2)
        self.assertEqual({f["composer"] for f in record["event_facts"]},
                         {"Francesco Filidei","Salvatore Sciarrino"})
        self.assertEqual({f["starts_at"] for f in record["event_facts"]},
                         {"2026-10-31T19:00:00+01:00"})

    def test_conflicting_credits_venue_and_clock_are_rejected(self):
        for html in (
            page().replace("Salvatore Sciarrino</p>","Francesco Filidei</p>",1),
            page().replace("Libretto di Pierre Senges","Libretto non indicato"),
            page().replace("Opera da camera</div>","Concerto</div>"),
            page().replace("Teatro M° Tonino Pardo","Altro Teatro"),
            page().replace("31 ottobre 2026, Ore 19:00",
                           "31 ottobre 2026, Ore non dichiarate"),
            page().replace("31 ottobre 2026, Ore 19:00",
                           "31 ottobre 2027, Ore 19:00"),
        ):
            with self.subTest(html=html[:170]),self.assertRaises(ValueError):
                parse_filidei_sciarrino_program(html,url=URL)
        with self.assertRaises(ValueError):
            parse_filidei_sciarrino_program(
                page(),url=INDEX+"ghost-cafe/")

if __name__=="__main__":
    unittest.main()
