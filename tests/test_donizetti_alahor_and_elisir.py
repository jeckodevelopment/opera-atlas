"""First-party Alahor and cached Trieste Elisir are complete source-scoped operas."""
import json
import unittest
from datetime import date

from opera_atlas.donizetti_credited_detail import parse_credited_detail
from scripts.auto_catalogue import (
    normalize_source_seed_trieste_genre,official_identity_candidates,
    promote_new_works,SOURCE_ALLOWLIST)
from scripts.auto_work_research import OUT as RESEARCH
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS,parse_source_credited_opera_detail
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import ROOT,REGISTRY
from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
from scripts.publish_work_posters import load_archival_art

ALAHOR="https://www.donizettiopera.org/it/evento/alahor-in-granata/2026-11-14/"
ELISIR="https://www.teatroverdi-trieste.com/it/spettacoli/lelisir-damore-3/"

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def event_page():
    return ("<h1>Alahor in Granata</h1>"
            "<p>OPERA 2026</p><p>Melodramma in due atti di M.A.</p>"
            "<p>Musica di Gaetano Donizetti</p>"
            "<p>Prima rappresentazione: Palermo, Teatro Carolino, 7 gennaio 1826</p>"
            "<h2>Cast</h2><p>Direttrice Chiara Cattani</p>"
            "<h2>Trama</h2><p>Granada, 1480</p>"
            "<h2>Info</h2><p>data</p>"
            "<p>14 novembre 2026 | 20:00</p>"
            "<p>22 novembre 2026 | 15:30</p>"
            "<p>27 novembre 2026 | 20:00</p>"
            "<p>Luogo</p><p>Teatro Sociale</p>")

class OfficialFestivalWorks(unittest.TestCase):
    def test_alahor_full_first_party_identity_and_three_dates(self):
        title,composer,venue,dates=parse_credited_detail(event_page(),url=ALAHOR)
        self.assertEqual((title,composer,venue),
                         ("Alahor in Granata","Gaetano Donizetti","Teatro Sociale"))
        self.assertEqual(dates,[("2026-11-14","20:00"),
                                ("2026-11-22","15:30"),
                                ("2026-11-27","20:00")])
        rows=parse_source_credited_opera_detail("donizetti-opera-2026",ALAHOR,event_page())
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[-1]["starts_at"],"2026-11-27T20:00:00+01:00")

    def test_cached_elisir_requires_exact_title_url_composer_and_genre(self):
        seeds=read(ROOT/"data/verified-work-authority-seeds.json")["works"]
        seed=next(x for x in seeds if x["source_url"]==ELISIR)
        evidence=read(DETAILS)
        observed=next(x for x in evidence["evidence"] if x["source_url"]==ELISIR)
        rows=observed["event_facts"]
        self.assertEqual({r["composer"] for r in rows},
                         {"Gaetano Donizetti Melodramma"})
        fixed=normalize_source_seed_trieste_genre(rows,seed["source_key"],ELISIR,seed)
        self.assertEqual({r["composer"] for r in fixed},{"Gaetano Donizetti"})
        self.assertEqual([x["starts_at"] for x in fixed],
                         [x["starts_at"] for x in rows])
        for bad in (
            {**seed,"source_url":"https://untrusted.invalid/other"},
            {**seed,"composer":"Giacomo Puccini"},
            {**seed,"title":"Altra opera"},
        ):
            self.assertEqual(normalize_source_seed_trieste_genre(
                rows,seed["source_key"],ELISIR,bad),rows)
        self.assertEqual(normalize_source_seed_trieste_genre(
            rows,"opera-roma-season-2026-27",ELISIR,seed),rows)

    def test_short_original_plot_premiere_and_historical_cover_provenance(self):
        seeds=read(ROOT/"data/verified-work-authority-seeds.json")["works"]
        for url,slug,title,year,city in (
            (ALAHOR,"alahor-in-granata","Alahor in Granata",1826,"Palermo"),
            (ELISIR,"elisir-d-amore","L’elisir d’amore",1832,"Milano"),
        ):
            with self.subTest(url=url):
                x=next(x for x in seeds if x["source_url"]==url)
                self.assertEqual(x["title"],title)
                self.assertEqual(x["history"]["premiere_year"],year)
                self.assertEqual(x["history"]["premiere_city"],city)
                self.assertTrue(validate_history(x["history"]))
                self.assertTrue(45<=len(x["synopsis"])<=300)
                archive=load_archival_art({slug})
                self.assertEqual(archive[slug]["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org",archive[slug]["source_url"])

    def test_elisir_cached_source_can_promote_new_work_idempotently(self):
        registry=read(REGISTRY)
        facts=read(MANIFEST)
        if any(x["title"]=="L’elisir d’amore" and
               x["composer"]=="Gaetano Donizetti"
               for x in registry["works"].values()):
            return
        evidence=read(DETAILS)
        candidates=read(CANDIDATES)
        intelligence=official_identity_candidates(
            evidence,candidates,{"schema_version":1,"works":[]})
        match=[x for x in intelligence["works"] if x.get("source_url")==ELISIR]
        self.assertEqual(len(match),1)
        self.assertEqual(match[0]["composer"],"Gaetano Donizetti")
        self.assertTrue(match[0]["history"])
        selected={"schema_version":1,"works":match}
        after=promote_new_works(
            facts,registry,evidence,candidates,selected,read(EDITORIAL),
            read(SOURCE_ALLOWLIST)["urls"],today=date(2026,11,21),
            history=read(HISTORY),require_image=True)
        new_facts,new_reg,approved,new_ed,new_history,report=after
        self.assertEqual(report["new_works"],1,report)
        self.assertEqual(report["new_recite"],6,report)
        self.assertEqual(len([p for p in new_facts["productions"]
                              if p["source_url"]==ELISIR]),1)
        again=promote_new_works(
            new_facts,new_reg,evidence,candidates,selected,new_ed,approved,
            today=date(2026,11,21),history=new_history,require_image=True)
        self.assertEqual(again[-1]["new_works"],0)

if __name__=="__main__":
    unittest.main()
