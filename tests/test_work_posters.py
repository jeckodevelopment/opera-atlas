"""A newly published opera must have a safe cover source and resilient fallback."""
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import publish_work_posters as posters
from opera_atlas.controlled_fetch import FetchResult

class PosterPublicationTests(unittest.TestCase):
    def test_extracts_explicit_official_poster_with_credit(self):
        url="https://www.teatrolafenice.it/event/adriana-lecouvreur/"
        html='''<html><head>
        <meta property="og:image" content="/wp-content/uploads/adriana-lecouvreur-poster.jpg">
        <meta property="og:image:alt" content="Adriana Lecouvreur - locandina">
        <meta property="og:image:width" content="800">
        <meta property="og:image:height" content="1200">
        </head></html>'''
        got=posters.extract_official_poster(html,url,"Adriana Lecouvreur")
        self.assertEqual(got["kind"],"official_production_image")
        self.assertEqual(got["image_url"],
                         "https://www.teatrolafenice.it/wp-content/uploads/adriana-lecouvreur-poster.jpg")
        self.assertEqual(got["source_url"],url)
        self.assertIn("teatro",got["credit"])

    def test_never_accepts_logos_trackers_unsafe_hosts_or_landscape_banners(self):
        url="https://www.teatrolafenice.it/event/norma/"
        bad=[
            '<meta property="og:image" content="http://www.teatrolafenice.it/poster.jpg">',
            '<meta property="og:image" content="https://tracking.example/poster.jpg">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/logo.png">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/poster.svg">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/poster.jpg" />'
            '<meta property="og:image:width" content="1600">'
            '<meta property="og:image:height" content="600">',
        ]
        for html in bad:
            with self.subTest(html=html):
                self.assertIsNone(posters.extract_official_poster(html,url,"Norma"))
        self.assertIsNone(posters.allowed_image_url(
            "https://www.teatrolafenice.it.evil.example/x.jpg",url))
        self.assertIsNone(posters.allowed_image_url(
            "https://www.teatrolafenice.it:8443/poster.jpg",url))

    def test_publishes_one_image_record_per_canonical_work_not_candidates(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)
            stored=folder/"evidence.json"
            published=folder/"work-posters.json"
            health=folder/"health.json"
            catalogue=[
                {"slug":"adriana-lecouvreur","work_id":"oa-w-000033",
                 "title":"Adriana Lecouvreur","source_key":"fenice-opera-2026-27",
                 "official_root":"https://www.teatrolafenice.it/",
                 "source_url":"https://www.teatrolafenice.it/event/adriana-lecouvreur/"},
                {"slug":"norma","work_id":"oa-w-000031","title":"Norma",
                 "source_key":"fenice-opera-2026-27",
                 "official_root":"https://www.teatrolafenice.it/",
                 "source_url":"https://www.teatrolafenice.it/event/normatebar/"},
            ]
            html='''<meta property="og:image" content="/wp-content/uploads/adriana-poster.jpg">
            <meta property="og:image:width" content="700">
            <meta property="og:image:height" content="1000">'''
            calls=[]
            def mock(db,*,source_id,url,network_enabled):
                calls.append(url)
                if "adriana" in url:
                    return FetchResult(url,html,"x"*64,len(html))
                return FetchResult(url,"<html><head></head></html>","y"*64,26)
            class FakeDB:
                def execute(self,*a,**k):
                    class Cursor:
                        def fetchone(self):return {"id":1}
                    return Cursor()
                def close(self):pass
            with patch.object(posters,"EVIDENCE",stored),patch.object(posters,"OUTPUT",published),\
                 patch.object(posters,"HEALTH",health),patch.object(posters,"canonical_sources",return_value=catalogue),\
                 patch.object(posters,"connect",return_value=FakeDB()),patch.object(posters,"migrate"):
                result=posters.publish(network_enabled=True,fetcher=mock,
                                       today=date(2026,11,21),max_pages=2)
                self.assertEqual(result["works"]["adriana-lecouvreur"]["kind"],
                                 "official_production_image")
                self.assertEqual(result["works"]["norma"]["kind"],
                                 "original_editorial_cover")
                self.assertEqual(len(calls),2)
                self.assertTrue(published.exists())
                evidence=json.loads(stored.read_text())
                self.assertEqual(len(evidence["posters"]),1)
                posters.publish(network_enabled=True,fetcher=mock,
                                today=date(2026,11,21),max_pages=2)
                self.assertEqual(len(calls),2) # no repeat within cooldown

    def test_frontend_loads_posters_without_redeploying_on_each_new_work(self):
        root=Path(__file__).resolve().parents[1]
        image_js=(root/"site/image-client.js").read_text(encoding="utf-8")
        self.assertIn("public/catalog/work-posters.json",image_js)
        self.assertIn("chosen.kind===\"official_production_image\"",image_js)
        for name in ("app.js","detail.js","directory.js"):
            text=(root/"site"/name).read_text(encoding="utf-8")
            self.assertIn("await window.OperaAtlasImages?.load?.()",text)

if __name__=="__main__":
    unittest.main()
