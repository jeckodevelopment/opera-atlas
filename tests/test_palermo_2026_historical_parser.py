"""Work-specific 2026 Palermo official showtime parsing with audience control."""
import unittest
from opera_atlas.palermo_2026_historical_parser import parse_palermo_historical_showtimes
from scripts.audit_2026_jan_jun_official import credited_official_opera_facts

def page(title,composer,dates,year=2026):
    return "<html><body><h2>Date</h2>"+ "".join(
        f"<li>{day} {month}</li><span>{hour}</span><p>{audience}</p>"
        for day,month,hour,audience in dates
    )+f"<h2>Lo spettacolo</h2><p>11, 12 marzo {year} | Sala Grande</p>" + \
           f"<h1>{title}</h1><p>Musiche di {composer}</p></body></html>"

class Palermo2026ParserTests(unittest.TestCase):
    def test_exact_2026_full_dates_and_non_school_filter(self):
        url="https://www.teatromassimo.it/event/aida/"
        html=page("Aida","Giuseppe Verdi",[
            (22,"Maggio","20:00","Turno Prime"),
            (26,"Maggio","18:30","Turno Scuola"),
            (27,"Maggio","18:30","Turno C")])
        title,composer,venue,dates=parse_palermo_historical_showtimes(html,url)
        self.assertEqual(("Aida","Giuseppe Verdi","Teatro Massimo"),
                         (title,composer,venue))
        self.assertEqual([("2026-05-22","20:00"),("2026-05-27","18:30")],dates)
        credits=credited_official_opera_facts(html,url)
        self.assertEqual(2,len(credits))
        self.assertEqual({x["date"] for x in credits},{"2026-05-22","2026-05-27"})

    def test_unreviewed_host_year_and_work_fail_closed(self):
        html=page("Semiramide","Gioachino Rossini",
                  [(11,"Marzo","20:00","Turno Prime")])
        with self.assertRaises(ValueError):
            parse_palermo_historical_showtimes(html,"https://other.example/event/semiramide/")
        with self.assertRaises(ValueError):
            parse_palermo_historical_showtimes(
                html,"https://www.teatromassimo.it/event/random/")
        with self.assertRaises(ValueError):
            parse_palermo_historical_showtimes(page("Semiramide","Gioachino Rossini",
                [(11,"Marzo","20:00","Prime")],year=2027),
                "https://www.teatromassimo.it/event/semiramide/")
        with self.assertRaises(ValueError):
            parse_palermo_historical_showtimes(page("Semiramide","Unrelated Composer",
                [(11,"Marzo","20:00","Prime")]),
                "https://www.teatromassimo.it/event/semiramide/")

if __name__=="__main__":
    unittest.main()
