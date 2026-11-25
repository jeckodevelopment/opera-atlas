"""Opera images are never replaced by the festival venue's image."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class FestivalArtworkTests(unittest.TestCase):
    def test_festival_performance_card_identified_as_work(self):
        source=(SITE/"directory.js").read_text(encoding="utf-8")
        self.assertIn('imageKind:event.program_id?"program":"work",programEvent:event,work_slug:event.work_slug',source)
        self.assertIn('const type=item.imageKind||',source)
        self.assertIn('{title:item.title,work_slug:item.work_slug,work_id:item.work_id',source)
        self.assertIn('images[type](identity)',source)
    def test_aida_has_unique_opera_poster_and_arena_is_venue(self):
        source=(SITE/"image-client.js").read_text(encoding="utf-8")
        self.assertIn('"aida":"Giuseppe Verdi - Hippodrome Opera Company - Aida poster.jpg"',source)
        self.assertIn('"verona":"Arena di Verona esterno.jpg"',source)
        self.assertIn('WORKS[slug]',source)
        self.assertIn('posters[event?.work_id]',source)
        self.assertIn('event?.photo_file',source)
        self.assertIn('event.photo_source_url.startsWith("https://commons.wikimedia.org/wiki/File:")',source)
        self.assertIn('kind:"verified_festival_venue"',source)
        self.assertNotIn('const file=FILES[city]',source)
    def test_catalogue_uses_stable_work_slug(self):
        manifest=json.loads((ROOT/"public/catalog/v2/manifest.json").read_text(encoding="utf-8"))
        works=json.loads((ROOT/"public/catalog/v2"/manifest["files"]["works"]["path"]).read_text(encoding="utf-8"))["works"]
        self.assertIn("aida",{w["slug"] for w in works})

if __name__=="__main__":
    unittest.main()
