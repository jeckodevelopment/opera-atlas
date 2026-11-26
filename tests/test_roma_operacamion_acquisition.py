import unittest
from opera_atlas.roma_operacamion import parse, eligible
from scripts.discover_season_indexes import reviewed_source_urls
from scripts.build_verified_catalog import MANIFEST
import json

URL="https://www.operaroma.it/spettacoli/il-barbiere-di-siviglia-operacamion/"
SECOND="https://www.operaroma.it/spettacoli/il-barbiere-di-siviglia-operacamion-2/"

def html(cards):
    return ("<p>Stagione 2025/2026</p><h1>Il barbiere di Siviglia – OperaCamion</h1>"
            "<p>da Il Barbiere di Siviglia</p><p>di Gioachino Rossini</p>"
            "<p>adattamento musicale Tommaso Chieco e Marco Giustini</p>"
            "<p>OperaCamion è un progetto del Teatro dell’Opera di Roma</p>"
            "<h3>Le date</h3>"+cards+"<h2>Ti può interessare anche</h2>")

def card(label,place,day,clock):
    return f"<h4>{label} - {place}</h4><p>{day}</p><p>ORE {clock}</p>"

class OperaCamionAcquisitionTests(unittest.TestCase):
    def test_cards_ordinary_and_preview(self):
        page=html(card("ANTEPRIMA","Magazzini (Municipio V)","domenica 31 Mag","21:15")+
            card("INGRESSO LIBERO (PORTATE LA SEDIA DA CASA)","Piazza Mazzini, Bracciano","martedì 09 Giu","21:15")+
            card("INGRESSO LIBERO","Municipio XI – Piazza Gaetano Mosca","domenica 13 Set","20:00")+
            card("INGRESSO LIBERO","Piazza non identificata","martedì 15 Set","20:00"))
        tour=parse(page,url=URL)
        self.assertEqual(tour["composer"],"Gioachino Rossini")
        self.assertEqual(len(tour["previews"]),1)
        self.assertEqual([x["municipality"] for x in tour["performances"]],["Bracciano","Roma",None])
        self.assertEqual(tour["performances"][0]["date"],"2026-06-09")
        self.assertEqual(tour["performances"][1]["starts_at"],"2026-09-13T20:00:00+02:00")
        self.assertTrue(eligible(URL))
        self.assertFalse(eligible(URL.replace("www.operaroma.it","example.com")))
        with self.assertRaises(ValueError):parse(page.replace("martedì 09 Giu","mercoledì 09 Giu"),url=URL)
        with self.assertRaises(ValueError):parse(page.replace("INGRESSO LIBERO","SCUOLE"),url=URL)
        with self.assertRaises(ValueError):parse(page.replace("adattamento musicale","arrangiamento"),url=URL)
    def test_both_published_rounds_close(self):
        manifest=json.loads(MANIFEST.read_text())
        if any(p.get("project_name")=="OperaCamion" for p in manifest["productions"]):
            self.assertTrue({URL,SECOND}.issubset(reviewed_source_urls()))
