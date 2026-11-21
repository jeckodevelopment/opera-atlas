"""Rome official first-party split composer credits, never inferred from a conductor."""
import json
import unittest
from scripts.collect_candidate_details import parse_source_credited_opera_detail
from opera_atlas.roma_detail_parser import parse_roma_credited_detail
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_work_editorial import validate_history

URL="https://www.operaroma.it/spettacoli/una-lady-macbeth-del-distretto-di-mzensk/"
SOURCE="opera-roma-season-2026-27"
TITLE="Una Lady Macbeth del distretto di Mzensk"
COMPOSER="Dmitrij Šostakovič"

def page(credit=None):
    if credit is None:
        credit="<p>Musica di</p><p>"+COMPOSER+"</p>"
    return ("<p>Stagione 2026/2027</p><h1>"+TITLE+"</h1>"
            +credit+
            "<p>Opera in quattro atti</p><p>Libretto di Aleksandr Prejs</p>"
            "<p>direttore Juraj Valčuha</p><h3>Dove</h3><p>Teatro Costanzi</p>"
            "<h3>Le date</h3><p>venerdì 14 Mag ORE 20:00 Turno A</p>"
            "<h3>Ti può interessare anche</h3><p>altra opera</p>")

class RomeSplitComposerCreditTests(unittest.TestCase):
    def test_split_credit_is_validated_and_dated_by_official_venue(self):
        title,composer,venue,dates=parse_roma_credited_detail(page(),url=URL)
        self.assertEqual((title,composer,venue),(TITLE,COMPOSER,
                         "Teatro dell'Opera di Roma"))
        self.assertEqual(dates,[("2027-05-14","20:00")])
        facts=parse_source_credited_opera_detail(SOURCE,URL,page())
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]["composer"],COMPOSER)
        self.assertEqual(facts[0]["starts_at"],"2027-05-14T20:00:00+02:00")

    def test_credit_must_be_explicit_and_adjacent(self):
        invalid=[
            page("<p>direttore Juraj Valčuha</p>"),
            page("<p>Musica di</p><p>direttore Juraj Valčuha</p>"),
            page("<p>Musica di</p><p>Compositore da definire</p>"),
            page("<p>Musica di</p><p>Dmitrij Šostakovič</p>"
                 "<p>Musica di</p><p>Altro Compositore</p>"),
            page().replace("Stagione 2026/2027","Stagione 2025/2026"),
            page().replace("Teatro Costanzi","Teatro Sconosciuto"),
        ]
        for html in invalid:
            with self.subTest(html=html[:120]),self.assertRaises(ValueError):
                parse_roma_credited_detail(html,url=URL)

    def test_completed_editorial_is_bound_to_exact_source_and_history(self):
        seed=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        found=[w for w in seed["works"] if w.get("source_url")==URL]
        self.assertEqual(len(found),1)
        self.assertEqual((found[0]["title"],found[0]["composer"]),(TITLE,COMPOSER))
        self.assertTrue(45<=len(found[0]["synopsis"])<=300)
        self.assertTrue(validate_history(found[0]["history"]))
        self.assertEqual(found[0]["history"]["premiere_year"],1934)
        self.assertEqual(found[0]["history"]["premiere_city"],"Leningrado")

if __name__=="__main__":
    unittest.main()
