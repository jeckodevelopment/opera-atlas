"""Canonical SEO HTML must be crawlable before JavaScript starts."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from scripts.prerender_atlas import generate, validated_route, DEFAULT_IMAGE

ROOT=Path(__file__).resolve().parents[1]

class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append((tag,dict(attrs)))

class StaticEntitySEOTests(unittest.TestCase):
    def test_safe_routes(self):
        for bad in ("/opere/../","/opere/x?y/","/evil//route/","/opere/à/"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validated_route(bad)
        self.assertEqual(validated_route("/opere/la-traviata/"),"opere/la-traviata/")

    def test_canonical_entities_are_pre_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            (target/"detail.html").write_text((ROOT/"site"/"detail.html").read_text(encoding="utf-8"),encoding="utf-8")
            routes=generate(target,ROOT/"public"/"catalog"/"v2")
            self.assertGreater(len(routes),350)
            self.assertEqual(len(routes),len(set(routes)))
            for route,expect in (
                ("opere/la-traviata/index.html","La traviata"),
                ("torino/teatro-regio/index.html","Torino"),
                ("roma/circo-massimo/index.html","Circo Massimo"),
                ("trapani/teatro-m-tonino-pardo/index.html","Tonino Pardo"),
                ("torino/teatro-regio/la-traviata/index.html","La traviata"),
                ("produzioni/oa-g-lombardia-italiana-2026/index.html","OperaLombardia"),
            ):
                page=target/route
                with self.subTest(route=route):
                    self.assertTrue(page.is_file())
                    doc=page.read_text(encoding="utf-8")
                    self.assertIn(expect,doc)
                    self.assertNotIn('<h1 id="detail-title">Caricamento…</h1>',doc)
                    self.assertIn('id="atlas-prerender"',doc)
                    parser=HeadParser();parser.feed(doc)
                    meta=[attrs for tag,attrs in parser.tags if tag=="meta"]
                    canon=[attrs["href"] for tag,attrs in parser.tags if tag=="link" and attrs.get("rel")=="canonical"]
                    self.assertEqual(len(canon),1)
                    self.assertEqual(canon[0],"https://opera.plus/atlas/"+route.removesuffix("index.html"))
                    self.assertEqual(len([m for m in meta if m.get("property")=="og:image"]),1)
                    self.assertEqual(len([m for m in meta if m.get("name")=="description"]),1)
            self.assertIn("opere/la-traviata/index.html",routes)

    def test_venue_directory_fallback_and_legacy_alias(self):
        rules=(ROOT/"site"/".htaccess").read_text(encoding="utf-8")
        self.assertIn("RewriteRule ^trapani/teatro-tonino-pardo/?$ /atlas/trapani/teatro-m-tonino-pardo/ [R=301,L,NE]",rules)
        self.assertIn("RewriteCond %{REQUEST_FILENAME} -d\nRewriteCond %{REQUEST_FILENAME}/index.html !-f\nRewriteRule ^[a-z0-9-]+/[a-z0-9-]+/?$ detail.html [L]",rules)

    def test_live_client_replaces_initial_summary(self):
        code=(ROOT/"site"/"detail.js").read_text(encoding="utf-8")
        self.assertIn('getElementById("atlas-prerender")?.remove()',code)

if __name__=="__main__":
    unittest.main()
