"""Previously unseen works are evidence only until independently attributed."""
import unittest
from opera_atlas.italian_detail_parser import extract_source_credited_carlo_felice
from scripts.collect_candidate_details import parse_source_credited_opera_detail

FIGARO="https://www.carlofelice.it/spettacolo/le-nozze-di-figaro/"
CAPULETI="https://www.carlofelice.it/spettacolo/i-capuleti-e-i-montecchi/"

def page(title,composer,rows):
    tickets="".join('<p>'+d+' Turno A | Ore '+h+' | Biglietti</p>'
                    for d,h in rows)
    return (tickets+'<p>Dove: Teatro Carlo Felice</p>'
            '<h1>'+title+'</h1><p>Tragedia lirica in due atti</p>'
            '<p>Musica di</p><p>'+composer+'</p>'
            '<p>Direttore</p><p>Renato Palumbo</p>')

class OfficialComposerEvidenceTests(unittest.TestCase):
    def test_figaro_is_credited_to_mozart_with_six_explicit_recite(self):
        rows=[("VE 16/10/2026","19:30"),("SA 17/10/2026","15:00"),
              ("DO 18/10/2026","15:00"),("VE 23/10/2026","19:30"),
              ("SA 24/10/2026","19:30"),("DO 25/10/2026","15:00")]
        html=page("Le nozze di figaro","Wolfgang Amadeus Mozart",rows)
        title,composer,venue,recite=extract_source_credited_carlo_felice(
            html,url=FIGARO)
        self.assertEqual(title,"Le nozze di figaro")
        self.assertEqual(composer,"Wolfgang Amadeus Mozart")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(len(recite),6)
        self.assertEqual(recite[0],("2026-10-16","19:30"))
        facts=parse_source_credited_opera_detail(
            "carlo-felice-season-2026-27",FIGARO,html)
        self.assertEqual(len(facts),6)
        self.assertTrue(all(x["composer"]=="Wolfgang Amadeus Mozart" for x in facts))

    def test_capuleti_is_credited_to_bellini_and_not_conductor(self):
        html=page("I Capuleti e i Montecchi","Vincenzo Bellini",[
            ("VE 20/11/2026","20:00"),("DO 22/11/2026","15:00"),
            ("ME 25/11/2026","20:00"),("VE 27/11/2026","20:00")])
        title,composer,venue,recite=extract_source_credited_carlo_felice(
            html,url=CAPULETI)
        self.assertEqual((title,composer),("I Capuleti e i Montecchi","Vincenzo Bellini"))
        self.assertEqual(len(recite),4)
        self.assertEqual(recite[-1],("2026-11-27","20:00"))
        facts=parse_source_credited_opera_detail(
            "carlo-felice-season-2026-27",CAPULETI,html)
        self.assertEqual({x["composer"] for x in facts},{"Vincenzo Bellini"})

    def test_offsite_wrong_heading_missing_or_conflicting_credit_is_rejected(self):
        html=page("I Capuleti e i Montecchi","Vincenzo Bellini",[
            ("VE 20/11/2026","20:00")])
        for changed in (
            html.replace("Musica di","Regia di"),
            html.replace("Direttore</p>","Maestro del coro</p>"),
            html.replace("I Capuleti e i Montecchi","Le nozze di figaro"),
            html.replace("Ore 20:00","Orario da definire"),
            html.replace("Musica di</p><p>Vincenzo Bellini",
                         "Musica di</p><p>Vincenzo Bellini</p><p>Direttore</p>"
                         "<p>Renato Palumbo</p><p>Musica di</p><p>Autore Errato")
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    extract_source_credited_carlo_felice(changed,url=CAPULETI)
        with self.assertRaises(ValueError):
            extract_source_credited_carlo_felice(
                html,url="https://outside.example/spettacolo/i-capuleti-e-i-montecchi/")
        self.assertEqual(parse_source_credited_opera_detail(
            "fenice-opera-2026-27",CAPULETI,html),[])

if __name__=="__main__":
    unittest.main()
