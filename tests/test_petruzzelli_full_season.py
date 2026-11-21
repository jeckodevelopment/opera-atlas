"""Petruzzelli must retain all genuine operas, not just Nabucco.

Official credit in H1 or a labelled opera presentation; no ballet,
historical 2022 events, combined bills, or inferred composer from slug.
"""
import copy
import json
import unittest
from datetime import date
from opera_atlas.petruzzelli_detail_parser import extract_official_petr_opera
from scripts.collect_candidate_details import (
    parse_known_opera_detail,parse_source_credited_opera_detail)
from scripts.auto_work_research import official_title_hint
from scripts.auto_catalogue import promote,SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

ROOT="https://www.fondazionepetruzzelli.it/eventi/"
SOURCE="petruzzelli-opera-2027"
BOHEME=ROOT+"la-boheme-17-27-dicembre/"
FIGARO=ROOT+"le-nozze-di-figaro-di-wolfgang-amadeus-mozart-12-19-settembre/"
MIXED=ROOT+"larlesienne-di-georges-bizet-pagliacci-di-ruggero-leoncavallo-13-20-ottobre/"
TALK="presenta l’opera"
SHOWS=[
    ("VENERDì",17,"DICEMBRE","20:30"),
    ("SABATO",18,"DICEMBRE","18:00"),
    ("DOMENICA",19,"DICEMBRE","18:00"),
    ("MARTEDì",21,"DICEMBRE","20:30"),
    ("MERCOLEDì",22,"DICEMBRE","20:30"),
    ("GIOVEDì",23,"DICEMBRE","20:30"),
    ("DOMENICA",26,"DICEMBRE","19:00"),
    ("LUNEDì",27,"DICEMBRE","18:00"),
]
def html(title,composer,shows,*,h1_composer=True,ballet=False):
    heading=title+(" di "+composer if h1_composer else "")+" | STAGIONE 2027"
    bill="".join(f"<p>{weekday} {day} {month} 2027 - {clock} | TURNO</p>"
                 for weekday,day,month,clock in shows)
    label="presenta il balletto" if ballet else TALK
    return (f"<h1>{heading}</h1><p>{composer}</p>"
            f"<p>Direttore Un Altro Musicista</p><p>Orchestra Petruzzelli</p>"
            f"<p>giovedì 9 dicembre 2027 | ore 19.00</p>"
            f"<p>CONFERENZIERE {label}</p><p>{title} di {composer}</p>"
            "<p>O&B 2027</p><h2>Orari Spettacoli</h2>"
            +bill+"<h3>Interpretato Da</h3>")

class FullPetruzzelliSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_puccini_boheme_eight_dates_never_leoncavallo(self):
        page=html("La Bohème","Giacomo Puccini",SHOWS,h1_composer=False)
        title,composer,venue,dates=extract_official_petr_opera(page,url=BOHEME)
        self.assertEqual((title,composer,venue),
                         ("La Bohème","Giacomo Puccini","Teatro Petruzzelli"))
        self.assertEqual(len(dates),8)
        rows=parse_known_opera_detail(SOURCE,BOHEME,page,self.registry)
        self.assertEqual(len(rows),8)
        self.assertEqual({x["composer"] for x in rows},{"Giacomo Puccini"})
        self.assertEqual([x["starts_at"][11:16] for x in rows],
                         [x[3] for x in SHOWS])

    def test_unknown_figaro_produces_full_first_party_evidence(self):
        page=html("Le nozze di Figaro","Wolfgang Amadeus Mozart",
                  [("DOMENICA",12,"SETTEMBRE","20:30"),
                   ("MARTEDì",14,"SETTEMBRE","20:30")])
        rows=parse_source_credited_opera_detail(SOURCE,FIGARO,page)
        self.assertEqual(len(rows),2)
        self.assertEqual({x["composer"] for x in rows},
                         {"Wolfgang Amadeus Mozart"})
        self.assertEqual(rows[0]["starts_at"],"2027-09-12T20:30:00+02:00")
        known=parse_known_opera_detail(SOURCE,FIGARO,page,self.registry)
        self.assertIn(len(known),(0,2))  # before/after canonical work promotion

    def test_authority_title_only_from_verified_first_party_rows(self):
        candidate={"id":"bari-fixture","source_key":SOURCE,"official_url":FIGARO}
        evidence={"evidence":[{"candidate_id":"bari-fixture","source_key":SOURCE,
                  "source_url":FIGARO,"status":"needs_editorial_review",
                  "event_facts":[{"event_title":"Le nozze di Figaro",
                                  "composer":"Wolfgang Amadeus Mozart"}]}]}
        self.assertEqual(official_title_hint(candidate,evidence),"Le nozze di Figaro")
        self.assertIsNone(official_title_hint(candidate,None))
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"].append(
            {"event_title":"Il barbiere di Siviglia","composer":"Gioachino Rossini"})
        self.assertIsNone(official_title_hint(candidate,bad))
        candidate["official_url"]=ROOT+"other-identity/"
        self.assertIsNone(official_title_hint(candidate,evidence))

    def test_reject_mixed_bill_ballet_uncredited_and_incomplete_ticket(self):
        figaro=html("Le nozze di Figaro","Wolfgang Amadeus Mozart",
                    [("DOMENICA",12,"SETTEMBRE","20:30")])
        for page,url in (
            (figaro.replace("presenta l’opera","presenta il balletto").replace(
                "Le nozze di Figaro di Wolfgang Amadeus Mozart | STAGIONE",
                "Le nozze di Figaro | STAGIONE"),FIGARO),
            (figaro.replace("DOMENICA 12 SETTEMBRE 2027 - 20:30",
                            "DOMENICA 12 SETTEMBRE 2027 - da definire"),FIGARO),
            (figaro.replace("presenta l’opera</p><p>Le nozze di Figaro di Wolfgang Amadeus Mozart",
                            "presenta l’opera</p><p>Le nozze di Figaro di Altro Autore"),FIGARO),
            (figaro,"https://evil.example/eventi/le-nozze/"),
            (html("L’Arlésienne di Georges Bizet | Pagliacci",
                  "Ruggero Leoncavallo",SHOWS),MIXED),
        ):
            with self.subTest(url=url,page=page[:80]):
                with self.assertRaises(ValueError):
                    extract_official_petr_opera(page,url=url)

    def test_all_verified_petruzzelli_2027_pages_persisted_without_mixing_ballet(self):
        from scripts.collect_candidate_details import OUTPUT as DETAILS
        from scripts.discover_season_indexes import OUTPUT as INDEX
        candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        expected={
            "la-boheme-17-27-dicembre":("La bohème","Giacomo Puccini",8),
            "le-nozze-di-figaro-di-wolfgang-amadeus-mozart-12-19-settembre":
                ("Le nozze di Figaro","Wolfgang Amadeus Mozart",6),
            "fidelio-di-ludwig-van-beethoven-19-25-novembre":
                ("Fidelio","Ludwig van Beethoven",5),
            "zenobia-di-niccolo-piccinni-27-29-31-gennaio-2-febbraio":
                ("Zenobia","Niccolò Piccinni",4),
            "arlecchino-di-ferruccio-busoni-15-18-21-23-maggio":
                ("Arlecchino","Ferruccio Busoni",4),
        }
        latest={x["source_url"].rstrip("/").split("/")[-1]:x
                for x in evidence["evidence"]
                if x["source_key"]==SOURCE}
        official={x["official_url"].rstrip("/").split("/")[-1]:x
                  for x in candidates["candidates"]
                  if x["source_key"]==SOURCE}
        self.assertEqual(sum(v[2] for v in expected.values()),27)
        for slug,(title,composer,n) in expected.items():
            self.assertIn(slug,official)
            self.assertIn(slug,latest)
            row=latest[slug]
            self.assertEqual(row["status"],"needs_editorial_review")
            self.assertEqual(len(row["event_facts"]),n)
            self.assertEqual({x["event_title"] for x in row["event_facts"]},
                             {title})
            self.assertEqual({x["composer"] for x in row["event_facts"]},
                             {composer})
            self.assertEqual({x["venue"] for x in row["event_facts"]},
                             {"Teatro Petruzzelli"})
            self.assertTrue(all(x["starts_at"].startswith(x["date"]+"T")
                                and x["starts_at"][-6:] in ("+01:00","+02:00")
                                for x in row["event_facts"]))
        mixed=next(x for x in evidence["evidence"]
                   if "larlesienne-di-georges-bizet-pagliacci" in x["source_url"])
        self.assertNotEqual(mixed["status"],"needs_editorial_review")

    def test_official_puccini_boheme_can_enter_public_feed_once(self):
        # Use live committed candidate/evidence (no invented work identity).
        from scripts.collect_candidate_details import OUTPUT as DETAILS
        from scripts.discover_season_indexes import OUTPUT as INDEX
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        facts,ids,urls,report=promote(
            self.facts,self.registry,evidence,candidates,approved,
            today=date(2026,11,21))
        prod=[p for p in facts["productions"] if p["source_url"]==BOHEME]
        self.assertEqual(len(prod),1)
        self.assertEqual(prod[0]["composer"],"Giacomo Puccini")
        self.assertEqual(len(prod[0]["dates"]),8)
        self.assertIn(BOHEME,urls)
        after,other,_,repeat=promote(facts,ids,evidence,candidates,urls,
                                     today=date(2026,11,21))
        self.assertEqual(repeat["new_recite"],0)
        self.assertEqual(after,facts)
        self.assertEqual(other,ids)
