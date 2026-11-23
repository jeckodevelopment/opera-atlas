"""SEO regression checks: static metadata, canonical sitemap and OG preview."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
from xml.etree import ElementTree as ET

from scripts.atlas_seo import build as build_seo

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CATALOG = ROOT / "public" / "catalog" / "v2"
PAGES = ("index.html", "in-scena.html", "directory.html",
         "detail.html", "privacy.html", "credits.html")


class AtlasSEOTests(unittest.TestCase):
    def test_every_page_has_shared_social_metadata(self):
        for page in PAGES:
            text = (SITE / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertEqual(text.count('name="description"'), 1)
                self.assertIn('property="og:title"', text)
                self.assertIn('property="og:description"', text)
                self.assertIn('property="og:image"', text)
                self.assertIn('name="twitter:card" content="summary_large_image"', text)
                self.assertIn('https://opera.plus/atlas/og-atlas.png', text)
                if page != "detail.html":
                    self.assertIn('rel="canonical"', text)

    def test_build_png_and_verified_sitemap(self):
        with tempfile.TemporaryDirectory() as name:
            out = Path(name)
            build_seo(out, CATALOG)
            data = (out / "og-atlas.png").read_bytes()
            self.assertTrue(data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"))
            self.assertEqual(struct.unpack(">II", data[16:24]), (1200, 630))
            root = ET.parse(out / "sitemap.xml").getroot()
            urls = [item.text for item in root.iter()
                    if item.tag.endswith("loc")]
            self.assertEqual(len(urls), len(set(urls)))
            self.assertIn("https://opera.plus/atlas/", urls)
            self.assertIn("https://opera.plus/atlas/in-scena", urls)
            self.assertIn("https://opera.plus/atlas/opere/la-traviata/", urls)
            self.assertIn("https://opera.plus/atlas/torino/teatro-regio/", urls)
            self.assertTrue(all(url.startswith("https://opera.plus/atlas/") for url in urls))

    def test_metadata_follows_canonical_entity_resolution(self):
        detail = (SITE / "detail.js").read_text(encoding="utf-8")
        directory = (SITE / "directory.js").read_text(encoding="utf-8")
        self.assertIn("setDetailSEO(selected,first)", detail)
        self.assertIn("structured", detail)
        self.assertIn("directorySEO(", directory)
        self.assertIn("section=festival&id=", directory)


if __name__ == "__main__":
    unittest.main()
