"""Official Rome 2027 works: source-specific venue and genre integrity."""
import json
import unittest
from pathlib import Path
from opera_atlas.roma_detail_parser import parse_roma_credited_detail
from scripts.discover_season_indexes import excluded_nonopera
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_work_editorial import validate_history

URL="https://www.operaroma.it/spettacoli/code-unknown/"
SOURCE="opera-roma-season-2026-27"

class TeatroNazionaleTests(unittest.TestCase):
    def test_first_party_new_opera_has_five_dates_and_real_auditorium(self):
        page=('<p>Stagione 2026/2027</p><h1>Code: Unknown</h1>'
              '<p>Musica di Nicola Sani</p>'
              '<h3>Dove</h3><p>Teatro Nazionale</p><h3>Le date</h3>'
              '<p>mercoledì 19 Mag ORE 20:00</p>'
              '<p>venerdì 21 Mag ORE 18:00</p>'
              '<p>domenica 23 Mag ORE 16:30</p>'
              '<p>martedì 25 Mag ORE 20:00</p>'
              '<p>mercoledì 26 Mag ORE 20:00</p>')
        title,composer,venue,dates=parse_roma_credited_detail(page,url=URL)
        self.assertEqual((title,composer,venue),
                         ("Code: Unknown","Nicola Sani","Teatro Nazionale"))
        self.assertEqual(dates,[("2027-05-19","20:00"),("2027-05-21","18:00"),
                                ("2027-05-23","16:30"),("2027-05-25","20:00"),
                                ("2027-05-26","20:00")])

    def test_preverified_card_and_theatre_provenance(self):
        works=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())["works"]
        card=[w for w in works if w.get("source_url")==URL]
        self.assertEqual(len(card),1)
        self.assertEqual((card[0]["title"],card[0]["composer"]),
                         ("Code: Unknown","Nicola Sani"))
        self.assertTrue(validate_history(card[0]["history"]))
        venues=json.loads((ROOT/"data/venue-directory.json").read_text())["venues"]
        theatre=[v for v in venues if v["city"]=="Roma" and v["name"]=="Teatro Nazionale"]
        self.assertEqual(len(theatre),1)
        self.assertEqual(theatre[0]["source_url"],
                         "https://www.operaroma.it/luoghi/teatro-nazionale/")
        # An actual institutional venue photo may be verified later; do
        # not regress the test to its original no-photo checkpoint.
        self.assertIn(theatre[0]["photo_status"],("review_pending","verified"))
        if theatre[0]["photo_status"]=="verified":
            self.assertTrue(theatre[0].get("photo_url","").startswith("https://"))
            self.assertTrue(theatre[0].get("photo_source_url","").startswith("https://"))
            self.assertTrue(theatre[0].get("photo_credit"))
            self.assertTrue(theatre[0].get("photo_license"))

    def test_theatrical_cenerentole_is_not_rossini(self):
        self.assertTrue(excluded_nonopera(SOURCE,
            "https://www.operaroma.it/spettacoli/le-cenerentole-quattro-donne-una-storia/"))
        self.assertFalse(excluded_nonopera(SOURCE,
            "https://www.operaroma.it/spettacoli/la-cenerentola-3/"))

if __name__=="__main__":
    unittest.main()
