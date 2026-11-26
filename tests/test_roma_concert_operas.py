import unittest
from opera_atlas.roma_detail_parser import CONCERT_WORKS,parse_roma_credited_detail
from scripts.seed_roma_historical_candidates import seed

class RomeConcertTests(unittest.TestCase):
    def test_reviewed_concerts(self):
        for url,(title,composer,marker) in CONCERT_WORKS.items():
            date,day=("2026-12-04","venerdì 04 Dic") if "barbablu" in url else ("2027-05-27","giovedì 27 Mag")
            html=f"<p>Stagione 2026/2027</p><h1>{title}</h1><p>{marker}</p><h3>Dove</h3><h3>Teatro Costanzi</h3><h3>Le date</h3><p>{day} ORE 20:00</p>"
            self.assertEqual(parse_roma_credited_detail(html,url=url),(title,composer,"Teatro dell'Opera di Roma",[(date,"20:00")]))
            with self.assertRaises(ValueError):
                parse_roma_credited_detail(html.replace(marker,"Concerto generico"),url=url)
    def test_exact_urls_seeded(self):
        candidates,_=seed({"candidates":[]},{"evidence":[]},set(),timestamp="now")
        self.assertTrue(set(CONCERT_WORKS).issubset({x["official_url"] for x in candidates["candidates"]}))
