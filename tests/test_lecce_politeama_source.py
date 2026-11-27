"""Lecce Politeama: exact three official title URLs and six ticket times."""
import unittest
from opera_atlas.lecce_politeama_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

ROOT="https://www.politeamagreco.it"
INDEX=ROOT+"/programmazione.asp?categoria=1"
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
    def test_category_calendar_respects_access_denial(self):
        import json
        from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable, AccessDenied
        from scripts.discover_season_indexes import CONFIG, scan
        config=json.loads(CONFIG.read_text())
        key="lecce-politeama-opera-2026"
        links=''.join(f'<a href="{DETAIL(i)}">Opera</a>' for i in (1148, 2050))
        for failure in (None, FetchUnavailable("page unavailable"), AccessDenied("robots denied")):
            requested=[]
            def fetch(db, *, source_id, url, network_enabled):
                requested.append(url)
                self.assertEqual(url, INDEX)
                if failure is not None: raise failure
                return FetchResult(url,links,"a"*64,len(links))
            candidates,health=scan(config,{"schema_version":1,"candidates":[]},
                                   fetcher=fetch,network_enabled=True,source_keys={key})
            self.assertEqual(health[0]["status"],"success" if failure is None else "unavailable_or_invalid")
            self.assertEqual(requested,[INDEX])
            self.assertEqual(len(candidates["candidates"]),2 if failure is None else 0)

    def test_future_unknown_id_individual_ticket_evidence(self):
        from scripts.collect_candidate_details import parse_source_credited_opera_detail
        future=("<p>Orario Spettacoli » 12/11/2027 - 20:45 » 14/11/2027 - 18:00</p>"
                "<p>CARMEN di Georges Bizet dal 12/11/2027 al 14/11/2027 - Stagione Lirica</p>"
                "<p>TEATRO POLITEAMA GRECO DI LECCE Stagione Lirica di tradizione 2027 "
                "CARMEN di Georges Bizet</p>"
                "<p>12 novembre ore 20.45 (Turno A) 14 novembre ore 18.00 (Turno B)</p>"
                "<h2>PREZZI</h2>")
        url=DETAIL(2050)
        self.assertTrue(eligible("lecce-politeama-opera-2026",url))
        self.assertEqual(extract("lecce-politeama-opera-2026",INDEX,
                                 f'<a href="{url}">Carmen</a>',1),[url])
        self.assertEqual(parse_detail(future,url=url),
                         ("Carmen","Georges Bizet","Teatro Politeama Greco",
                          [("2027-11-12","20:45"),("2027-11-14","18:00")]))
        facts=parse_source_credited_opera_detail("lecce-politeama-opera-2026",url,future)
        self.assertEqual(len(facts),2)
        self.assertEqual({r["composer"] for r in facts},{"Georges Bizet"})
        for invalid in (
            future.replace("14 novembre ore 18.00","14 novembre ore 19.00"),
            future.replace("Stagione Lirica di tradizione 2027","Stagione Lirica di tradizione 2028"),
            future.replace("CARMEN","CONCERTO"),
            future.replace("TEATRO POLITEAMA GRECO","TEATRO APOLLO"),
            future.replace("Turno A","recite scuole"),
            future.replace("14/11/2027 - 18:00",""),
            future.replace("PREZZI","Altro"),
        ):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                parse_detail(invalid,url=url)

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
