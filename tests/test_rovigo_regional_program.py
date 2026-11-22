"""Regional programme is verifiable discovery, not performance evidence."""
import json
import unittest
from opera_atlas.rovigo_regional_program import (
    URL,approved_programme,PDF_BASENAME
)
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract

PDF=("https://resc.deskline.net/documents/1/TRN/"
     "a7fc383d-8358-4237-839a-b3cde3c188bb/"+PDF_BASENAME)
PAGE=(
    "<h1>Teatro Sociale di Rovigo. Stagione Teatrale</h1>"
    "<p>Dal: 24/10/2026 Al: 16/05/2027</p>"
    f'<a href="{PDF}">Programma_stagione_2026_27_da_scaricare</a>'
)

class RegionalProgramTests(unittest.TestCase):
    def test_official_document_discovery_from_fixed_regional_page(self):
        config=validate_config(json.loads(CONFIG.read_text()))
        self.assertTrue(any(s["key"]=="rovigo-regione-programma-2026-27"
                            for s in config))
        self.assertTrue(eligible("rovigo-regione-programma-2026-27",URL))
        self.assertFalse(eligible("rovigo-regione-programma-2026-27",URL+"?q=other"))
        self.assertEqual(approved_programme(PAGE,url=URL),PDF)
        self.assertEqual(extract("rovigo-regione-programma-2026-27",URL,PAGE,1),[URL])

    def test_overview_date_range_never_establishes_recite(self):
        for broken in (
            PAGE.replace("Teatro Sociale di Rovigo","Teatro Comunale di Modena"),
            PAGE.replace("2027","2025"),
            PAGE.replace("resc.deskline.net","untrusted.example"),
            PAGE.replace(PDF_BASENAME,"unrelated.pdf"),
            PAGE.replace("Programma_stagione_2026_27_da_scaricare","Documenti"),
        ):
            with self.subTest(value=broken[:55]):
                with self.assertRaises(ValueError):
                    approved_programme(broken,url=URL)
        with self.assertRaises(ValueError):
            approved_programme(PAGE,url=URL.replace("https://","http://"))
        with self.assertRaises(ValueError):
            approved_programme(PAGE+f'<a href="{PDF}other">Programma_stagione_2026_27_da_scaricare</a>',url=URL)

if __name__=="__main__":
    unittest.main()
