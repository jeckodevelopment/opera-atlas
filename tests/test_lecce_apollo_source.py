"""First-party 2026 contemporary opera: Apollo, never Politeama."""
import unittest
from opera_atlas.lecce_apollo_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

URL=("https://www.provincia.le.it/al-via-la-51-stagione-lirica-della-"
     "provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/")
TEXT="""<h1>Al via la 51^ Stagione Lirica della Provincia di Lecce</h1>
<p>La Stagione 2026 si aprirà il 13 novembre (ore 20.45) con
Turandot di Giacomo Puccini al Teatro Politeama Greco, con replica il 15.
L'elisir d'amore e Nabucco sono al Politeama Greco.</p>
<h2>LA CHICCA FUORI ABBONAMENTO: LE AVVENTURE DI PINOCCHIO</h2>
<p>Il bicentenario della nascita di Carlo Collodi ha offerto l'occasione
per proporre una rilettura musicale del suo celebre libro Le avventure
di Pinocchio. In programma mercoledì 30 dicembre, ore 20.45,
presso il Teatro Apollo di Lecce. Si tratta dell'opera omonima
composta da Antonio Cericola, su libretto di Sandro Bernabei.</p>
<p>La nuova produzione conclude la stagione.</p>"""

class LecceApolloSourceTests(unittest.TestCase):
    def test_one_approved_article_not_neighboring_theatre(self):
        self.assertTrue(eligible("lecce-apollo-pinocchio-2026",URL))
        for bad in (URL+"?utm=1",URL.replace("www.provincia.le.it","fake.example"),
                    URL.replace("https://","http://"),URL.replace("turandot-di-puccini","altro")):
            self.assertFalse(eligible("lecce-apollo-pinocchio-2026",bad))
        self.assertEqual(extract("lecce-apollo-pinocchio-2026",URL,TEXT,1),[URL])
    def test_work_composer_and_only_apollo_performance(self):
        self.assertEqual(parse_detail(TEXT,url=URL),
            ("Le avventure di Pinocchio","Antonio Cericola","Teatro Apollo",
             [("2026-12-30","20:45")]))
    def test_fail_closed_without_full_showtime_or_attribution(self):
        for bad in (
            TEXT.replace("Antonio Cericola","Giacomo Puccini"),
            TEXT.replace("mercoledì 30 dicembre, ore 20.45","mercoledì 30 dicembre"),
            TEXT.replace("Teatro Apollo di Lecce","Teatro Politeama Greco di Lecce"),
            TEXT.replace("LA CHICCA FUORI ABBONAMENTO: LE AVVENTURE DI PINOCCHIO",
                         "LA CHICCA FUORI ABBONAMENTO: LA TRAVIATA"),
            TEXT.replace("51^ Stagione Lirica","50^ Stagione Lirica"),
            TEXT.replace("ore 20.45","ore 21.00"),
        ):
            with self.assertRaises(ValueError):
                parse_detail(bad,url=URL)
        with self.assertRaises(ValueError):
            parse_detail(TEXT,url=URL+"?ref=other")
if __name__=="__main__":
    unittest.main()
