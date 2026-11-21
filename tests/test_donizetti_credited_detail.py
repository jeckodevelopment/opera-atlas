"""Donizetti Opera 2026 first-party identity, history, image and performance proofs."""
import json
import unittest
from datetime import date

from opera_atlas.donizetti_credited_detail import parse_credited_detail
from scripts.collect_candidate_details import parse_source_credited_opera_detail
from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.auto_work_research import OUT as RESEARCH

URL="https://www.donizettiopera.org/it/evento/le-convenienze-ed-inconvenienze-teatrali/"
TITLE="Le convenienze ed inconvenienze teatrali"
SOURCE="donizetti-opera-2026"
DATES=[("2026-11-15","15:30"),("2026-11-20","20:00"),("2026-11-28","20:00")]

def page(*,composer="Gaetano Donizetti"):
    return ("<h1>"+TITLE+"</h1>"
            "<p>Dramma giocoso in un atto di Domenico Gilardoni</p>"
            "<p>Musica di "+composer+"</p>"
            "<p>Prima rappresentazione della nuova versione: Napoli</p>"
            "<h2>Cast</h2><p>Direttore Alberto Zanardi</p>"
            "<h2>Trama</h2><p>Una compagnia si riunisce per provare il melodramma</p>"
            "<h2>Info</h2><p>data</p>"
            +"".join("<p>"+day+" | "+clock+"</p>" for day,clock in (
                ("15 novembre 2026","15:30"),("20 novembre 2026","20:00"),
                ("28 novembre 2026","20:00")))
            +"<p>Luogo</p><p>Teatro Donizetti</p>")

class DonizettiCreditsTests(unittest.TestCase):
    def test_credits_and_showtimes_are_first_party_and_individual(self):
        title,composer,venue,dates=parse_credited_detail(page(),url=URL)
        self.assertEqual((title,composer,venue),(TITLE,"Gaetano Donizetti","Teatro Donizetti"))
        self.assertEqual(dates,DATES)
        rows=parse_source_credited_opera_detail(SOURCE,URL,page())
        self.assertEqual(len(rows),3)
        self.assertEqual({x["composer"] for x in rows},{"Gaetano Donizetti"})
        self.assertEqual(rows[-1]["starts_at"],"2026-11-28T20:00:00+01:00")

    def test_real_collection_dispatches_new_work_adapter(self):
        from opera_atlas.controlled_fetch import FetchResult
        from scripts.collect_candidate_details import collect
        candidate={"schema_version":1,"candidates":[{
            "id":"oa-index-test-donizetti","source_key":SOURCE,
            "official_url":URL,"status":"needs_review"}]}
        html=page()
        visited=[]
        def fake(db,*,source_id,url,network_enabled):
            visited.append(url)
            return FetchResult(url,html,"a"*64,len(html))
        result,health=collect(candidate,{"schema_version":1,"evidence":[]},
                              network_enabled=True,fetcher=fake,
                              today=date(2026,11,20))
        self.assertEqual(visited,[URL])
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        record=result["evidence"][0]
        self.assertEqual(record["status"],"needs_editorial_review")
        self.assertEqual(len(record["event_facts"]),3)
        self.assertEqual({x["composer"] for x in record["event_facts"]},
                         {"Gaetano Donizetti"})

    def test_must_not_infer_author_from_cast_title_or_url(self):
        cases=[
            page().replace("Musica di Gaetano Donizetti",""),
            page(composer="Compositore da definire"),
            page().replace("Musica di Gaetano Donizetti","Musica di Direttore Alberto Zanardi"),
            page().replace("<h1>"+TITLE+"</h1>","<h1>Altra opera</h1>"),
            page().replace("Teatro Donizetti","Teatro inventato"),
            page().replace("28 novembre 2026 | 20:00","28 novembre 2026 | da definire"),
        ]
        for html in cases:
            with self.subTest(page=html[:90]),self.assertRaises(ValueError):
                parse_credited_detail(html,url=URL)
        with self.assertRaises(ValueError):
            parse_credited_detail(page(),url="https://other.example/it/evento/le-convenienze-ed-inconvenienze-teatrali/")

    def test_source_matched_synopsis_and_verified_historical_image(self):
        seeds=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        rows=[x for x in seeds["works"] if x["source_url"]==URL]
        self.assertEqual(len(rows),1)
        seed=rows[0]
        self.assertEqual((seed["title"],seed["composer"]),
                         (TITLE,"Gaetano Donizetti"))
        self.assertTrue(45<=len(seed["synopsis"])<=300)
        self.assertTrue(validate_history(seed["history"]))
        self.assertEqual((seed["history"]["premiere_year"],seed["history"]["premiere_city"]),
                         (1831,"Napoli"))
        self.assertEqual(seed["history"]["premiere_venue"],"Teatro del Fondo")
        self.assertIn(URL,seed["history"]["sources"])

        art=load_archival_art({"le-convenienze-ed-inconvenienze-teatrali"})
        self.assertEqual(art["le-convenienze-ed-inconvenienze-teatrali"]["kind"],
                         "archival_work_image")
        self.assertIn("commons.wikimedia.org",
                      art["le-convenienze-ed-inconvenienze-teatrali"]["source_url"])

if __name__=="__main__":
    unittest.main()
