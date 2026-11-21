"""Three source-verified Petruzzelli compositions and their authentic images."""
import json
import unittest
from pathlib import Path

from opera_atlas.verified_coproduction_posters import (
    verified_coproduction_poster,is_verified_coproduction_poster)
from scripts.auto_catalogue import verified_candidate_image
from scripts.publish_work_editorial import validate_history
from scripts.publish_work_posters import load_archival_art

ROOT=Path(__file__).resolve().parents[1]
SOURCE="https://www.fondazionepetruzzelli.it/eventi/"
SPECS=(
    ("bona-sforza-krautze-14-20-settembre/","BONA SFORZA","Zygmunt Krauze",2024),
    ("il-gobbo-del-califfo-casavola-21-24-maggio/","IL GOBBO DEL CALIFFO","Franco Casavola",1929),
    ("la-cecchina-piccinni-21-28-gennaio/","LA CECCHINA","Niccolò Piccinni",1760),
)
class ThreeBariOperas(unittest.TestCase):
    def test_complete_source_bound_identity_and_short_synopsis(self):
        doc=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        for path,title,composer,year in SPECS:
            record=[x for x in doc["works"] if x.get("source_url")==SOURCE+path]
            self.assertEqual(len(record),1)
            self.assertEqual((record[0]["source_key"],record[0]["title"],
                              record[0]["composer"]),("petruzzelli-opera-2026",title,composer))
            self.assertEqual(record[0]["history"]["premiere_year"],year)
            self.assertTrue(validate_history(record[0]["history"]))
            self.assertTrue(45<=len(record[0]["synopsis"])<=300)
    def test_genuine_archival_covers_for_two_historic_operas(self):
        found=load_archival_art({"la-cecchina","il-gobbo-del-califfo"})
        self.assertEqual(set(found),{"la-cecchina","il-gobbo-del-califfo"})
        self.assertTrue(all(x["kind"]=="archival_work_image" for x in found.values()))
        self.assertTrue(all(x["source_url"].startswith("https://commons.wikimedia.org/wiki/File:")
                            for x in found.values()))
        self.assertIn("1929",found["il-gobbo-del-califfo"]["alt"])
        self.assertIn("1760",found["la-cecchina"]["alt"])
    def test_official_bona_sforza_coproducer_poster(self):
        url=SOURCE+SPECS[0][0]
        card=verified_coproduction_poster(source_url=url,title="BONA SFORZA",
                                         composer="Zygmunt Krauze")
        self.assertIsNotNone(card)
        self.assertEqual(card["kind"],"official_coproduction_poster")
        self.assertEqual(card["provenance_url"],"https://opera.krakow.pl/spektakle/bona-sforza")
        self.assertEqual(verified_candidate_image({},title="BONA SFORZA",
            composer="Zygmunt Krauze",url=url),card)
        self.assertTrue(is_verified_coproduction_poster(
            card,title="BONA SFORZA",composer="Zygmunt Krauze"))
        for t,c,u in (
                ("BONA SFORZA","Franco Casavola",url),
                ("BONA SFORZA","Zygmunt Krauze",SOURCE+SPECS[1][0]),
                ("Bona Sforza Film","Zygmunt Krauze",url)):
            self.assertIsNone(verified_coproduction_poster(
                source_url=u,title=t,composer=c))
        self.assertFalse(is_verified_coproduction_poster(
            {**card,"image_url":"https://opera.krakow.pl/media/gallery_image/other.jpg"},
            title="BONA SFORZA",composer="Zygmunt Krauze"))

if __name__=="__main__":
    unittest.main()
