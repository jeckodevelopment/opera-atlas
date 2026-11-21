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

    def test_surname_and_date_heading_uses_full_credit_next_to_h1(self):
        url="https://www.fondazionepetruzzelli.it/eventi/falstaff-verdi-7-15-marzo/"
        html=(
            "<h1>FALSTAFF | VERDI | 7 – 15 MARZO</h1>"
            "<p>Giuseppe Verdi</p>"
            "<p>Commedia lirica in tre atti, libretto di Arrigo Boito</p>"
            "<p>direttore Altro Musicista</p>"
            "<h2>Orari Spettacoli</h2>"
            "<p>SABATO 7 MARZO 2026 - 20:30 | TURNO A</p>"
            "<p>DOMENICA 8 MARZO 2026 - 18:00 | fuori abb.</p>"
            "<h3>Interpretato Da</h3>")
        title,composer,venue,dates=extract_official_petr_opera(
            html,url=url,season_year=2026)
        self.assertEqual((title,composer,venue),
                         ("FALSTAFF","Giuseppe Verdi","Teatro Petruzzelli"))
        self.assertEqual(dates,[("2026-03-07","20:30"),
                                ("2026-03-08","18:00")])
        rows=parse_source_credited_opera_detail("petruzzelli-opera-2026",
                                                url,html)
        self.assertEqual(len(rows),2)
        self.assertEqual({x["composer"] for x in rows},{"Giuseppe Verdi"})

    def test_2026_official_visible_headline_without_h1(self):
        url="https://www.fondazionepetruzzelli.it/eventi/falstaff-verdi-7-15-marzo/"
        html=("<nav><a>AMMINISTRAZIONE TRASPARENTE</a></nav>"
              "<div>FALSTAFF | VERDI | 7 – 15 MARZO</div>"
              "<p>Giuseppe Verdi</p><p>direttore Vincenzo Milletarì</p>"
              "<h2>Orari Spettacoli</h2>"
              "<p>SABATO 7 MARZO 2026 - 20:30</p>"
              "<p>DOMENICA 8 MARZO 2026 - 18:00</p>"
              "<h3>Interpretato Da</h3>")
        result=extract_official_petr_opera(html,url=url,season_year=2026)
        self.assertEqual(result[0:3],("FALSTAFF","Giuseppe Verdi","Teatro Petruzzelli"))
        self.assertEqual(len(result[3]),2)
        rows=parse_source_credited_opera_detail("petruzzelli-opera-2026",url,html)
        self.assertEqual(len(rows),2)
        for bad in (
            html.replace("<p>Giuseppe Verdi</p>","<p>Giuseppe Rossini</p>"),
            html.replace("FALSTAFF | VERDI","FALSTAFF / PAGLIACCI | VERDI"),
            html.replace("SABATO 7 MARZO 2026 - 20:30","SABATO 7 MARZO 2026 - DA DEFINIRE")):
            with self.subTest(bad=bad[:110]),self.assertRaises(ValueError):
                extract_official_petr_opera(bad,url=url,season_year=2026)

    def test_surname_heading_never_infers_composer_or_multiple_opera(self):
        url="https://www.fondazionepetruzzelli.it/eventi/falstaff-verdi-7-15-marzo/"
        valid=("<h1>FALSTAFF | VERDI | 7 – 15 MARZO</h1>"
               "<p>Giuseppe Verdi</p><h2>Orari Spettacoli</h2>"
               "<p>SABATO 7 MARZO 2026 - 20:30</p>")
        variants=(
            valid.replace("<p>Giuseppe Verdi</p>","<p>Vincenzo Milletarì</p>"),
            valid.replace("<p>Giuseppe Verdi</p>","<p>Verdi</p>"),
            valid.replace("7 – 15 MARZO","PAGLIACCI"),
            valid.replace("FALSTAFF | VERDI | 7 – 15 MARZO",
                          "FALSTAFF / PAGLIACCI | VERDI | 7 – 15 MARZO"),
            valid.replace("20:30","orario da definire"))
        for html in variants:
            with self.subTest(html=html[:110]),self.assertRaises(ValueError):
                extract_official_petr_opera(html,url=url,season_year=2026)

    def test_no_credit_or_ballet_or_missing_clock(self):
        for html in (page().replace("La Bohème di Giacomo Puccini O&B 2027","La Bohème di Giacomo Puccini O&B 2027 presenta l’opera La Bohème di Altro Autore O&B 2027"),page(label="il balletto"),
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
