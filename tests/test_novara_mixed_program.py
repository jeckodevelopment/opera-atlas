"""Novara double bill is one ticket and two separately credited operas."""
import copy
import json
import unittest

from opera_atlas.novara_program_parser import URL,parse_program
from scripts.build_verified_catalog import official_local_time,MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from scripts.publish_programs import assemble_programs,REVIEWED_WORKS
from scripts.discover_season_indexes import CONFIG,OUTPUT as CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE


def official_page():
    return (
        "<div>Home / Spettacoli / Opera / L’AMOR MIO / IL TABARRO</div>"
        "<h1>L’AMOR MIO / IL TABARRO</h1>"
        "<p>L'AMOR MIO</p><p>Nuova commissione in prima esecuzione mondiale</p>"
        "<p>Musica di Cristian Carrara</p><p>Libretto di Nikolai Prestia</p>"
        "<p>IL TABARRO</p><p>Musica di Giacomo Puccini</p>"
        "<p>Libretto di Giuseppe Adami</p>"
        "<p>Prima rappresentazione New York, 14 dicembre 1918</p>"
        "<h3>informazioni sull'evento</h3>"
        "<h4>Venerdì 26 novembre 2027</h4><p>ore 20:00 (Turno A)</p>"
        "<h4>Domenica 28 novembre 2027</h4><p>ore 16:00 (Turno B)</p>"
        "<h3>TEATRO COCCIA</h3>"
    )


class NovaraMixedProgramTests(unittest.TestCase):
    def test_exact_official_source_and_complete_components(self):
        credits,venue,dates=parse_program(official_page(),url=URL)
        self.assertEqual(credits,[{"title":"L'amor mio","composer":"Cristian Carrara"},
                                  {"title":"Il tabarro","composer":"Giacomo Puccini"}])
        self.assertEqual(venue,"Teatro Coccia")
        self.assertEqual(dates,[("2027-11-26","20:00"),("2027-11-28","16:00")])
        for html in (
            official_page().replace("Musica di Giacomo Puccini","Musica di Unrelated"),
            official_page().replace("Opera /","Danza /"),
            official_page().replace("Domenica 28 novembre 2027","Domenica 29 novembre 2027"),
            official_page().replace("TEATRO COCCIA","ALTRO TEATRO"),
            official_page().replace("ore 16:00","ore 16:00 ore 20:00"),
            official_page().replace("Venerdì 26 novembre 2027","Annullato Venerdì 26 novembre 2027"),
        ):
            with self.subTest(html=html[-140:]),self.assertRaises(ValueError):
                parse_program(html,url=URL)
        with self.assertRaises(ValueError):
            parse_program(official_page(),url=URL+"?promo=yes")

    def test_central_program_publisher_preserves_two_works_one_ticket(self):
        read=lambda path:json.loads(path.read_text(encoding="utf-8"))
        candidates=copy.deepcopy(read(CANDIDATES))
        evidence=copy.deepcopy(read(EVIDENCE))
        components,venue,dates=parse_program(official_page(),url=URL)
        key="coccia-novara-rolling-opera"
        candidate=next(x for x in candidates["candidates"]
                       if x["source_key"]==key and x["official_url"]==URL)
        heading="/".join(x["title"] for x in components)+" di "+"/".join(
            x["composer"] for x in components)
        row={"candidate_id":candidate["id"],"source_key":key,"source_url":URL,
             "content_sha256":"a"*64,"status":"needs_program_review",
             "program_heading":heading,"program_heading_source_url":URL,
             "program_components":components,
             "event_facts":[{"event_title":x["title"],"composer":x["composer"],
                             "venue":venue,"date":day,
                             "starts_at":official_local_time(day,time)}
                            for day,time in dates for x in components]}
        evidence["evidence"]=[x for x in evidence["evidence"]
                              if x["candidate_id"]!=candidate["id"]]+[row]
        result=assemble_programs(candidates,evidence,read(REGISTRY),read(MANIFEST),
                                 read(CONFIG),read(REVIEWED_WORKS))
        item=next(x for x in result["programs"] if x["source_url"]==URL)
        self.assertEqual(len(item["components"]),2)
        self.assertEqual(len(item["performances"]),2)
        self.assertEqual({x["local_date"] for x in item["performances"]},
                         {"2027-11-26","2027-11-28"})
        self.assertEqual(item["municipality"],"Novara")
        self.assertEqual(item["venue"],"Teatro Coccia")
        self.assertEqual(len({x["id"] for x in item["performances"]}),2)
        again=assemble_programs(candidates,evidence,read(REGISTRY),read(MANIFEST),
                                read(CONFIG),read(REVIEWED_WORKS))
        self.assertEqual(result,again)


if __name__=="__main__":
    unittest.main()
