"""Messina: official index and exact dates, never inferred date intervals."""
import unittest
from opera_atlas.messina_opera_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

HOST="https://www.teatrovittorioemanuele.it"
INDEX=HOST+"/event_listing_type/opera-26-27/"
URL=lambda slug:HOST+"/evento/"+slug+"/"
SHOWS={
 "madama-butterfly":("Madama Butterfly","Giacomo Puccini",("26-02-2027","21:00","28-02-2027","17:30")),
 "la-traviata":("La Traviata","Giuseppe Verdi",("16-04-2027","21:00","18-04-2027","17:30")),
 "al-cavallino-bianco":("Al cavallino bianco","Ralph Benatzky",("07-05-2027","21:00","08-05-2027","21:00")),
}
def sample(slug):
    title,composer,(d1,h1,d2,h2)=SHOWS[slug]
    return (f"<h1>{title}</h1><p>di {composer}</p>"
      "<h3>Orario spettacoli e turni abbonati</h3>"
      f"<p>Data - {d1}</p><p>Orario - {h1}</p>"
      f"<p>Data - {d2}</p><p>Orario - {h2}</p>"
      "<p>Data -</p><p>Orario -</p><a>Acquista i biglietti</a>"
      f"<h3>Date spettacolo</h3><p>{d1} to {d2}</p>"
      "<h3>Location</h3><p>Sala Grande - Teatro Vittorio Emanuele</p>"
      "<h3>Tipologie di evento</h3><p>Opera 26/27</p>")
class MessinaOperaTests(unittest.TestCase):
    def test_exact_official_index_allowlist(self):
        html=''.join(f'<a href="{URL(s)}">{s}</a>' for s in SHOWS)
        html+='<a href="/evento/il-sogno-di-yerma/">Prosa</a>'
        self.assertEqual(extract("messina-vittorio-opera-2026-27",INDEX,html,3),
                         sorted(URL(s) for s in SHOWS))
        for bad in (HOST+"/evento/carmen/",URL("la-traviata")+"?ref=1",
                    URL("la-traviata").replace("https://","http://"),
                    "https://example.com/evento/la-traviata/"):
            self.assertFalse(eligible("messina-vittorio-opera-2026-27",bad))
    def test_exact_six_times_and_attributions(self):
        expected={
          "madama-butterfly":[("2027-02-26","21:00"),("2027-02-28","17:30")],
          "la-traviata":[("2027-04-16","21:00"),("2027-04-18","17:30")],
          "al-cavallino-bianco":[("2027-05-07","21:00"),("2027-05-08","21:00")],
        }
        for slug,dates in expected.items():
            with self.subTest(slug=slug):
                self.assertEqual(parse_detail(sample(slug),url=URL(slug))[-1],dates)
    def test_fail_closed_on_mismatched_time_date_composer_or_venue(self):
        html=sample("madama-butterfly")
        for bad in (html.replace("di Giacomo Puccini","di Giuseppe Verdi"),
                    html.replace("Orario - 17:30","Orario -"),
                    html.replace("28-02-2027","27-02-2027"),
                    html.replace("Opera 26/27","Prosa 26/27"),
                    html.replace("Sala Grande - Teatro Vittorio Emanuele",
                                 "Sala Laudamo - Teatro Vittorio Emanuele"),
                    html.replace("Orario - 17:30","Orario - 16:00")):
            with self.assertRaises(ValueError):
                parse_detail(bad,url=URL("madama-butterfly"))
        with self.assertRaises(ValueError):
            parse_detail(html,url=URL("madama-butterfly")+"?utm=1")
if __name__=="__main__":
    unittest.main()
