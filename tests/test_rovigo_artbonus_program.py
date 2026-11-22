"""First-party Comune authored season text is repertoire proof, not date proof."""
import unittest

from opera_atlas.rovigo_artbonus_program import URL,verified_programmes

BLOCK=(
    "<h3>Stagione lirica 2026/2027 - Eventi promozionali e titoli specifici</h3>"
    "<p>La stagione 2026/2027 del Teatro Sociale raccoglie un ventaglio"
    " di generi. La prima della Stagione sara a novembre e verra messa"
    " in scena l'opera Pagliacci di R. Leoncavallo, seguita dall'operetta"
    " Die Fledermaus, dall'intermezzo buffo Pimpinone di T. Albinoni"
    " e dal dittico The Telephone di Menotti - Trouble in Thaiti di Bernstein."
    " Il programma nel 2027 proseguira con \"Traviata\" di G.Verdi,"
    " \"Aida\" di G.Verdi, ed infine da Cenerentola di G.Rossini.</p>"
    "<h3>TeatroRagazzi 2026</h3><p>Pagina successiva</p>"
)

class RovigoMunicipalLineupTests(unittest.TestCase):
    def test_issuer_authorized_repertoire_without_recite_fabrication(self):
        doc=verified_programmes(BLOCK,url=URL)
        self.assertEqual(len(doc["works"]),7)
        self.assertEqual(doc["event_facts"],[])
        self.assertEqual(doc["composite"],
                         [["The Telephone","Trouble in Tahiti"]])
        self.assertEqual(doc["excluded"],
                         [{"title":"Die Fledermaus","genre":"operetta"}])
        self.assertEqual(doc["venue"],"Teatro Sociale di Rovigo")

    def test_archival_programmes_and_other_origins_do_not_qualify(self):
        for broken in (
            BLOCK.replace("2026/2027 - Eventi","2025/2026 - Eventi",1),
            BLOCK.replace("operetta Die Fledermaus","opera Die Fledermaus"),
            BLOCK.replace("dittico The Telephone","concerto The Telephone"),
            BLOCK.replace("The Telephone di Menotti","The Telephone"),
            BLOCK.replace("Cenerentola di G.Rossini","Cenerentola"),
            BLOCK.replace("<h3>TeatroRagazzi 2026</h3>",""),
        ):
            with self.subTest(broken=broken[:70]):
                with self.assertRaises(ValueError):
                    verified_programmes(broken,url=URL)
        with self.assertRaises(ValueError):
            verified_programmes(BLOCK,url=URL+"?other=1")

if __name__=="__main__":
    unittest.main()
