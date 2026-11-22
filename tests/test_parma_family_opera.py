"""Parma family opera must not double-count performances for schools."""
import unittest
from opera_atlas.parma_family_opera import URL,parse_family_opera
from scripts.collect_candidate_details import parse_official_parma_work_detail

def page():
    return (
      "<h1>Piccolo Orso e la montagna di ghiaccio</h1>"
      "<div>Dai 6 ai 14 anni</div><div>4 dic 2026</div><div>5 dic 2026</div>"
      "<h2>Spettacolo</h2><p>Storia dei due orsetti</p>"
      "<p>musica Giovanni Sollima</p><p>libretto Giancarlo De Cataldo</p>"
      "<p>ritiro dei biglietti per le scuole venerdì 27 novembre 2026</p>"
      "<h3>Teatro Regio di Parma</h3>"
      "<div>ven 4 dic</div><div>09:00</div><div>Scuole</div>"
      "<div>ven 4 dic</div><div>11:00</div><div>Scuole</div>"
      "<div>sab 5 dic</div><div>15:00</div><div>Famiglie</div>"
      "<div>sab 5 dic</div><div>18:00</div><div>Famiglie</div>"
      "<h2>Informazioni</h2><div>Teatro Regio di Parma</div>"
    )

class ParmaFamilyOperaTests(unittest.TestCase):
    def test_only_public_family_tickets_are_published(self):
        result=parse_family_opera(page(),url=URL)
        self.assertEqual(result,(
            "Piccolo Orso e la montagna di ghiaccio","Giovanni Sollima",
            "Teatro Regio di Parma",
            [("2026-12-05","15:00"),("2026-12-05","18:00")]))
        evidence=parse_official_parma_work_detail(URL,page())
        self.assertEqual(len(evidence),2)
        self.assertEqual({x["date"] for x in evidence},{"2026-12-05"})
        self.assertEqual({x["composer"] for x in evidence},{"Giovanni Sollima"})
    def test_unverified_facts_do_not_create_family_tickets(self):
        for html in (
            page().replace("musica Giovanni Sollima","musica Altro autore"),
            page().replace("libretto Giancarlo De Cataldo",""),
            page().replace("Teatro Regio di Parma","Altro teatro"),
            page().replace("sab 5 dic","dom 5 dic"),
            page().replace("Famiglie","Scuole"),
            page().replace("Famiglie</div>","Famiglie</div><div>20:00</div>",1),
            page().replace("sab 5 dic</div><div>18:00</div><div>Famiglie",
                           "sab 5 dic</div><div>15:00</div><div>Famiglie"),
            page().replace("ven 4 dic</div><div>11:00</div><div>Scuole",
                           "ven 4 dic</div><div>11:00</div><div>"),
            page().replace("15:00","Annullato 15:00"),
        ):
            with self.subTest(html=html[-85:]),self.assertRaises(ValueError):
                parse_family_opera(html,url=URL)
        for bad in (URL+"?ref=1",URL.replace("https://","http://"),
                    "https://elsewhere.example/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/"):
            with self.assertRaises(ValueError):
                parse_family_opera(page(),url=bad)

if __name__=="__main__":
    unittest.main()
