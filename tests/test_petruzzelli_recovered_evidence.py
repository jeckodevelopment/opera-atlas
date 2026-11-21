"""Regression of trusted first-party opera evidence against false attribution."""
import json
import unittest
from pathlib import Path
from opera_atlas.petruzzelli_detail_parser import extract_official_petr_opera
from scripts.collect_candidate_details import parse_source_credited_opera_detail

URL="https://www.fondazionepetruzzelli.it/eventi/la-boheme-17-27-dicembre/"
SOURCE="petruzzelli-opera-2027"

def page(*,credit="Giacomo Puccini",label="l’opera",clock="20:30"):
    return (
        "<h1>La Bohème | STAGIONE 2027</h1>"
        "<p>Direttore Un Altro Musicista</p>"
        "<p>presenta "+label+" La Bohème di "+credit+" O&B 2027</p>"
        "<h2>Orari Spettacoli</h2>"
        "<p>venerdì 17 dicembre 2027 - "+clock+"</p>"
        "<h3>Interpretato Da</h3>"
    )

class Recovery(unittest.TestCase):
    def test_official_composer_never_conductor_or_homonym(self):
        title,composer,venue,recite=extract_official_petr_opera(page(),url=URL)
        self.assertEqual((title,composer,venue),("La Bohème","Giacomo Puccini","Teatro Petruzzelli"))
        self.assertEqual(recite,[("2027-12-17","20:30")])
        rows=parse_source_credited_opera_detail(SOURCE,URL,page())
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["composer"],"Giacomo Puccini")

    def test_no_credit_or_ballet_or_missing_clock(self):
        for html in (page(credit="Un Altro Musicista"),page(label="il balletto"),
                     page(clock="da definire"),
                     page().replace("presenta l’opera La Bohème di Giacomo Puccini O&B 2027","")):
            with self.subTest(html=html[:80]):
                with self.assertRaises(ValueError):
                    extract_official_petr_opera(html,url=URL)

    def test_recovered_five_works_keep_2027_facts(self):
        root=Path(__file__).resolve().parents[1]
        doc=json.loads((root/"data/candidate-detail-evidence.json").read_text())
        rows=[r for r in doc["evidence"] if r.get("source_key")==SOURCE and
              r.get("status")=="needs_editorial_review"]
        found={r["event_facts"][0]["event_title"]:len(r["event_facts"]) for r in rows
               if r.get("event_facts")}
        for title,count in (("La bohème",8),("Le nozze di Figaro",6),("Fidelio",5),
                            ("Zenobia",4),("Arlecchino",4)):
            self.assertEqual(found.get(title),count)
        self.assertFalse(any("L'Arlésienne" in r.get("source_url","") and
                             r.get("status")=="needs_editorial_review" for r in rows))

if __name__=="__main__":
    unittest.main()
