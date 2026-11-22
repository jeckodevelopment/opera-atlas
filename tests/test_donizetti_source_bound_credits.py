"""Donizetti Opera official credits survive HTML block splitting, no title guessing."""
import unittest
from opera_atlas.donizetti_credited_detail import parse_credited_detail

ROOT="https://www.donizettiopera.org/it/evento/"
CASES=[
    ("alahor-in-granata/2026-11-14/","Alahor in Granata","Teatro Sociale",[
        ("2026-11-14","20:00"),("2026-11-22","15:30"),
        ("2026-11-27","20:00")]),
    ("le-convenienze-ed-inconvenienze-teatrali/",
     "Le convenienze ed inconvenienze teatrali","Teatro Donizetti",[
        ("2026-11-15","15:30"),("2026-11-20","20:00"),
        ("2026-11-28","20:00")])]
MONTHS={"11":"novembre"}

def fixture(title,venue,dates,*,composer="Gaetano Donizetti"):
    times="".join(f"<p>{int(day[-2:])} novembre {day[:4]} | {clock}</p>"
                  for day,clock in dates)
    # Deliberately separate music label across HTML blocks. Visible text
    # retains the explicit official "Musica di Gaetano Donizetti" attribution.
    return (f"<h1>{title}</h1><div>Melodramma in due atti</div>"
            f"<div>Musica</div><div>di</div><div>{composer}</div>"
            f"<p>Prima rappresentazione: Palermo 1826</p>"
            f"<h2>Cast</h2><p>Interpreti del festival</p>"
            f"<h2>Info</h2>{times}<h2>Luogo</h2><p>{venue}</p>")

class DonizettiSourceCreditTests(unittest.TestCase):
    def test_two_official_operas_and_six_exact_performances(self):
        for slug,title,venue,performances in CASES:
            with self.subTest(slug=slug):
                result=parse_credited_detail(fixture(title,venue,performances),url=ROOT+slug)
                self.assertEqual(result,(title,"Gaetano Donizetti",venue,performances))

    def test_wrong_composer_never_uses_title_as_identity(self):
        slug,title,venue,dates=CASES[0]
        with self.assertRaisesRegex(ValueError,"labelled Donizetti composer"):
            parse_credited_detail(fixture(title,venue,dates,composer="Wolfgang Mozart"),
                                  url=ROOT+slug)

    def test_unknown_official_page_cannot_borrow_approved_seed(self):
        slug,title,venue,dates=CASES[0]
        with self.assertRaises(ValueError):
            parse_credited_detail(fixture(title,venue,dates),
                                  url=ROOT+"unknown-work/")

if __name__=="__main__":
    unittest.main()
