"""Regression coverage for the five-item mobile navigation."""
import re
import unittest
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

SITE = Path(__file__).resolve().parents[1] / "site"


class MobileNavigationTests(unittest.TestCase):
    def test_all_pages_have_the_same_five_destinations(self):
        expected = [
            ("./#spettacoli", "Spettacoli"),
            ("./in-scena", "In scena"),
            ("./directory.html?section=opere", "Opere"),
            ("./directory.html?section=teatri", "Teatri"),
            ("./directory.html?section=festival", "Festival"),
        ]
        for name in ("index", "in-scena", "directory", "detail", "privacy", "credits"):
            with self.subTest(page=name):
                html = (SITE / (name + ".html")).read_text(encoding="utf-8")
                nav = re.search(r'<nav class="mobile-nav"[^>]*>(.*?)</nav>', html, re.S)
                self.assertIsNotNone(nav)
                self.assertEqual(expected, re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', nav.group(1)))

    def test_single_row_and_touch_targets(self):
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns:repeat(5,minmax(0,1fr))", css)
        self.assertNotIn(".mobile-nav{position:fixed;bottom:0;left:0;right:0;z-index:30;display:grid;grid-template-columns:repeat(4,", css)
        rule = re.search(r'\.mobile-nav a\{([^}]+)\}', css).group(1)
        self.assertIn("min-height:44px", rule)
        self.assertIn("white-space:nowrap", rule)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn(".mobile-nav{display:none}", css)

    def test_new_icons_are_valid_distinct_svg_masks(self):
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        icons = set()
        for key in ("spettacoli", "in-scena", "festival"):
            with self.subTest(section=key):
                selector = '.mobile-nav a[href*="' + key + '"]::before'
                prefix = selector + '{--nav-icon:url("data:image/svg+xml,'
                self.assertIn(prefix, css)
                svg = unquote(css.split(prefix, 1)[1].split('")}', 1)[0])
                root = ElementTree.fromstring(svg)
                self.assertEqual("{http://www.w3.org/2000/svg}svg", root.tag)
                self.assertEqual("0 0 24 24", root.attrib["viewBox"])
                icons.add(svg)
        self.assertEqual(3, len(icons))
        self.assertIn("-webkit-mask:var(--nav-icon)", css)
