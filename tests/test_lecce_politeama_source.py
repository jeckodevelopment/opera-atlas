"""Lecce Politeama: exact three official title URLs and six ticket times."""
import unittest
from opera_atlas.lecce_politeama_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

ROOT="https://www.politeamagreco.it"
INDEX=ROOT+"/programmazione.asp"
DETAIL=lambda number:ROOT+f"/scheda.asp?id={number}"

def html(number):
    title,composer,dates={
        1147:("TURANDOT","Giacomo Puccini",
              "13 novembre ore 20.45 (Turno A) 15 novembre ore 18.00 (Turno B)"),
        1148:("L'ELISIR D'AMORE","Gaetano Donizetti",
              "27 novembre ore 20.45 TURNO A 29 novembre ore 18.00 TURNO B"),
        1149:("NABUCCO","Giuseppe Verdi",
              "11 dicembre ore 20.45 TURNO A 13 dicembre ore 18.00 TURNO B"),
    }[number]
    return (f"<h1>{title} di {composer}</h1>"
            "<p>TEATRO POLITEAMA GRECO DI LECCE</p>"
            f"<p>Stagione Lirica di tradizione 2026 {title} di {composer}</p>"
            f"<p>{dates}</p><h2>PREZZI</h2>"
            "<p>Orari biglietteria 30 ottobre ore 18.00</p>")

class LeccePoliteamaTests(unittest.TestCase):
    def test_approved_parameter_query_only(self):
        index=''.join(f'<a href="/scheda.asp?id={i}">Opera</a>' for i in (1147,1148,1149))
        index+='<a href="/scheda.asp?id=1150">Conferenza</a>'
        index+='<a href="/scheda.asp?id=1146">Stagione intera</a>'
        index+='<a href="/scheda.asp?id=1147&utm=1">tracking</a>'
        self.assertEqual(extract("lecce-politeama-opera-2026",INDEX,index,3),
                         [DETAIL(i) for i in (1147,1148,1149)])
        for url in (DETAIL(1150),DETAIL(1146),DETAIL(1147)+"&ref=1",
                    ROOT+"/scheda.asp?ID=1147",ROOT+"/scheda.asp?id=01147",
                    "https://fake.example/scheda.asp?id=1147",
                    "http://www.politeamagreco.it/scheda.asp?id=1147"):
            self.assertFalse(eligible("lecce-politeama-opera-2026",url))
        self.assertTrue(eligible("lecce-politeama-opera-2026",DETAIL(1148)))
    def test_six_performances_and_attribution(self):
        self.assertEqual(parse_detail(html(1147),url=DETAIL(1147)),
            ("Turandot","Giacomo Puccini","Teatro Politeama Greco",
             [("2026-11-13","20:45"),("2026-11-15","18:00")]))
        self.assertEqual(parse_detail(html(1148),url=DETAIL(1148)),
            ("L'elisir d'amore","Gaetano Donizetti","Teatro Politeama Greco",
             [("2026-11-27","20:45"),("2026-11-29","18:00")]))
        self.assertEqual(parse_detail(html(1149),url=DETAIL(1149)),
            ("Nabucco","Giuseppe Verdi","Teatro Politeama Greco",
             [("2026-12-11","20:45"),("2026-12-13","18:00")]))
    def test_fail_closed_on_competing_events_or_bad_dates(self):
        for broken in (
            html(1149).replace("Giuseppe Verdi","Gioachino Rossini"),
            html(1149).replace("13 dicembre ore 18.00","13 dicembre ore 17.00"),
            html(1149).replace("2026","2025"),
            html(1149).replace("TEATRO POLITEAMA GRECO DI LECCE","TEATRO APOLLO DI LECCE"),
            html(1149).replace("13 dicembre ore 18.00","1 gennaio ore 18.00"),
        ):
            with self.assertRaises(ValueError):
                parse_detail(broken,url=DETAIL(1149))
        with self.assertRaises(ValueError):
            parse_detail(html(1149),url=DETAIL(1149)+"&source=other")

if __name__=="__main__":
    unittest.main()
