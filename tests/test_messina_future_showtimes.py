"""Future Messina productions have exact times and independent canonical credits."""
import unittest
from opera_atlas.messina_opera_parser import parse_detail
from scripts.collect_candidate_details import parse_known_opera_detail

URL="https://www.teatrovittorioemanuele.it/evento/nuova-traviata/"
REGISTRY={"works":{"traviata":{"title":"La traviata",
                                "composer":"Giuseppe Verdi","id":"oa-w-0001"}}}

def future_page(*,season="27/28",title="La traviata",
                composer="Giuseppe Verdi",times=None,
                venue="Sala Grande - Teatro Vittorio Emanuele"):
    if times is None:
        times=[("17-11-2027","21:00"),("19-11-2027","17:30")]
    rows="".join(f"<p>Data - {day}</p><p>Orario - {clock}</p>"
                 for day,clock in times)
    return (f"<h1>{title}</h1><p>di {composer}</p>"
            "<h3>Orario spettacoli e turni abbonati</h3>"+rows+
            "<p>Data -</p><p>Orario -</p>"
            "<h3>Date spettacolo</h3><p>17-11-2027 to 19-11-2027</p>"
            f"<h3>Location</h3><p>{venue}</p>"
            f"<h3>Tipologie di evento</h3><p>Opera {season}</p>")

class MessinaFutureShowtimesTests(unittest.TestCase):
    def test_next_season_known_opera_is_source_credited_and_exact(self):
        title,composer,venue,rows=parse_detail(future_page(),url=URL,
                                                registry=REGISTRY)
        self.assertEqual((title,composer,venue),
                         ("La traviata","Giuseppe Verdi","Teatro Vittorio Emanuele"))
        self.assertEqual(rows,[("2027-11-17","21:00"),
                               ("2027-11-19","17:30")])
        facts=parse_known_opera_detail("messina-vittorio-opera-2026-27",URL,
                                      future_page(),REGISTRY)
        self.assertEqual(len(facts),2)
        self.assertEqual([x["date"] for x in facts],
                         ["2027-11-17","2027-11-19"])

    def test_2028_29_works_without_a_new_hardcoded_year(self):
        html=future_page(season="28/29",times=[("10-10-2028","20:00")])
        self.assertEqual(parse_detail(html,url=URL,registry=REGISTRY)[3],
                         [("2028-10-10","20:00")])

    def test_future_parser_rejects_missing_registry_or_mismatched_identity(self):
        for registry in (None,{"works":{}},
                         {"works":{"x":{"title":"Aida","composer":"Giuseppe Verdi"}}}):
            with self.assertRaises(ValueError):
                parse_detail(future_page(),url=URL,registry=registry)
        for html in (future_page(composer="Giacomo Puccini"),
                     future_page(title="Concerto jazz"),
                     future_page(season="Prosa 27/28"),
                     future_page(venue="Sala Laudamo - Teatro Vittorio Emanuele")):
            with self.assertRaises(ValueError):
                parse_detail(html,url=URL,registry=REGISTRY)

    def test_future_parser_rejects_dates_outside_season_and_incomplete_times(self):
        samples=(
            [("10-11-2026","21:00")],
            [("10-07-2028","21:00")],
            [("17-11-2027","21:00"),("17-11-2027","21:00")],
        )
        for times in samples:
            with self.subTest(times=times),self.assertRaises(ValueError):
                parse_detail(future_page(times=times),url=URL,registry=REGISTRY)
        with self.assertRaises(ValueError):
            parse_detail(future_page().replace("Orario - 17:30","Orario -"),
                         url=URL,registry=REGISTRY)
        with self.assertRaises(ValueError):
            parse_detail(future_page().replace("Data - 17-11-2027",
                                              "Data - 32-11-2027"),
                         url=URL,registry=REGISTRY)

    def test_future_parser_rejects_cancellation_and_unsafe_url(self):
        with self.assertRaises(ValueError):
            parse_detail(future_page().replace("Data - 17-11-2027",
                          "Annullato Data - 17-11-2027"),url=URL,registry=REGISTRY)
        for url in (URL+"?ref=marketing","http://www.teatrovittorioemanuele.it/evento/nuova-traviata/",
                    "https://example.org/evento/nuova-traviata/"):
            with self.assertRaises(ValueError):
                parse_detail(future_page(),url=url,registry=REGISTRY)

if __name__=="__main__":
    unittest.main()
