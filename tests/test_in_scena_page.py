"""Non-regression checks for the In scena visitor route and data-bound imagery."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InScenaPageTests(unittest.TestCase):
    def test_menu_uses_supported_slashless_url(self):
        for filename in ("index.html", "directory.html", "detail.html", "in-scena.html"):
            page = (ROOT / "site" / filename).read_text(encoding="utf-8")
            self.assertIn('href="./in-scena"', page, filename)
            self.assertNotIn('href="./in-scena/"', page, filename)

    def test_trailing_slash_normalized_and_both_checked(self):
        routes = (ROOT / "site" / ".htaccess").read_text(encoding="utf-8")
        self.assertIn("RewriteRule ^in-scena/$ /atlas/in-scena", routes)
        self.assertIn("RewriteRule ^in-scena$ in-scena.html", routes)
        deployment = (ROOT / "scripts" / "deploy_atlas.py").read_text(encoding="utf-8")
        self.assertIn('in-scena/?release=', deployment)

    def test_search_and_dates_are_connected(self):
        page = (ROOT / "site" / "in-scena.html").read_text(encoding="utf-8")
        script = (ROOT / "site" / "in-scena.js").read_text(encoding="utf-8")
        for widget in ("today-query", "today-quick-days", "today-region", "today-city", "today-time", "day-input"):
            self.assertIn('id="' + widget + '"', page)
            self.assertIn('"' + widget + '"', script)
        self.assertIn('images?.load?.()', script)
        self.assertIn('artwork?.sourceUrl', script)
        self.assertIn('p.work_id', script)


if __name__ == "__main__":
    unittest.main()
