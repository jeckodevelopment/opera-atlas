"""Editorial visitor UI regression checks without external network calls."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts=[]
        self.images=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="script":self.scripts.append(d.get("src",""))
        if tag=="img":self.images.append(d)
        if tag=="a":self.links.append(d.get("href",""))

class EditorialUITests(unittest.TestCase):
    def test_image_client_available_on_every_catalog_page(self):
        for page in ("index.html","directory.html","detail.html"):
            m=Markup()
            m.feed((SITE/page).read_text(encoding="utf-8"))
            self.assertIn("./image-client.js",m.scripts,page)
            self.assertIn("./credits.html",m.links,page)
        self.assertTrue((SITE/"credits.html").exists())
        html=(SITE/"index.html").read_text(encoding="utf-8")
        self.assertIn("hero-image",html)
        self.assertIn("commons.wikimedia.org",html)
    def test_multi_column_catalogs(self):
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn(".events{display:grid;grid-template-columns:repeat(3",css)
        self.assertIn(".directory-grid{grid-template-columns:repeat(4",css)
        self.assertIn("#discover-works,#discover-venues,#discover-festivals",css)
        app=(SITE/"app.js").read_text(encoding="utf-8")
        directory=(SITE/"directory.js").read_text(encoding="utf-8")
        self.assertIn("editorialImage(",app)
        self.assertIn("imageFor(",directory)
    def test_official_sources_only_on_detail_bottom(self):
        app=(SITE/"app.js").read_text(encoding="utf-8")
        detail=(SITE/"detail.js").read_text(encoding="utf-8")
        directory=(SITE/"directory.js").read_text(encoding="utf-8")
        self.assertNotIn('"Fonte ufficiale"',app)
        self.assertNotIn('"Fonte ufficiale"',detail)
        self.assertNotIn('"Fonte ufficiale"',directory)
        self.assertNotIn("sourceLinks(section,events)",detail)
        self.assertIn("results.after(panel)",detail)
        self.assertIn("sourceLinks(selected.events)",detail)
        self.assertNotIn("Programma e biglietti sul sito ufficiale",detail)
    def test_no_technical_catalog_copy(self):
        directory=(SITE/"directory.js").read_text(encoding="utf-8")
        self.assertNotIn("Edizioni e programmi festivalieri verificati",directory)
        self.assertNotIn("rappresentazioni future censite",directory)
    @unittest.skipUnless(shutil.which("node"),"Node not installed")
    def test_js_syntax(self):
        for name in ("app.js","directory.js","detail.js","image-client.js"):
            result=subprocess.run(["node","--check",str(SITE/name)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,name+": "+result.stderr)

if __name__=="__main__":
    unittest.main()
