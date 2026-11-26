import unittest
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import verified_candidate_image
from opera_atlas.verified_original_work_art import is_verified_original_art

class RomeFinalEditorialArtTests(unittest.TestCase):
    def test_inferno_literary_source(self):
        art=load_archival_art({"inferno"})["inferno"]
        self.assertIn("Dor",art["credit"])
        self.assertIn("Ronchetti",art["alt"])
        self.assertIn("Public domain",art["license"])

    def test_trionfo_exact_historical_score(self):
        url="https://www.operaroma.it/spettacoli/il-trionfo-del-tempo-e-del-disinganno/"
        title="Il trionfo del Tempo e del Disinganno"
        composer="Georg Friedrich Händel"
        art=verified_candidate_image({},title=title,url=url,composer=composer)
        self.assertEqual(art["original_source_url"],"https://searcharchives.bl.uk/catalog/040-001948559")
        self.assertEqual(art["image_url"],"https://www.jarousskywiki.com/images/thumb/c/cc/First_page_il_trionfo.jpg/300px-First_page_il_trionfo.jpg")
        self.assertTrue(is_verified_original_art(art,title=title,composer=composer))
        self.assertIsNone(verified_candidate_image({},title=title,url=url,composer="Antonio Vivaldi"))
        self.assertIsNone(verified_candidate_image({},title=title,url=url+"fake/",composer=composer))

if __name__=="__main__":
    unittest.main()
