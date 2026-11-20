"""Privacy-by-default, association identity, logo and editorial ordering."""
import json
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="img":self.images.append(attrs)
        if tag=="a":self.links.append(attrs.get("href",""))

class AtlasLegalBrandTests(unittest.TestCase):
    def test_logo_in_every_public_page(self):
        logo=(SITE/"atlas-logo.svg").read_text()
        self.assertIn('data:image/png;base64,',logo)
        data=re.search(r'base64,([A-Za-z0-9+/=]+)',logo)
        self.assertIsNotNone(data)
        import base64
        image=base64.b64decode(data.group(1),validate=True)
        self.assertTrue(image.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertGreater(len(image),2000)
        for file in ("index.html","detail.html","directory.html","credits.html","privacy.html"):
            html=(SITE/file).read_text()
            parsed=Parser()
            parsed.feed(html)
            self.assertTrue(any(x.get("src")=="./atlas-logo.svg" for x in parsed.images),file)
            self.assertIn("Associazione Opera+",html)
            self.assertIn("97925160018",html)
            self.assertIn("./privacy.html",parsed.links)
    def test_home_theatre_order_and_single_opera_theatre_heading(self):
        app=(SITE/"app.js").read_text()
        css=(SITE/"styles.css").read_text()
        self.assertIn('x.municipality==="Torino" && x.venue==="Teatro Regio"',app)
        self.assertIn(".staging-group:not(.theatre-production) h3 a{font:inherit!important",css)
    def test_specific_licensed_images(self):
        js=(SITE/"image-client.js").read_text()
        self.assertIn('"verona":"Arena di Verona esterno.jpg"',js)
        self.assertIn('Georges Antoine Rochegrosse.jpg',js)
        self.assertIn("Arena_di_Verona_esterno.jpg",(SITE/"credits.html").read_text())
    def test_no_first_party_tracking_scripts(self):
        code="\n".join((SITE/f).read_text() for f in
           ("app.js","detail.js","directory.js","image-client.js","catalog-client.js","festival-client.js"))
        for pattern in ("document.cookie","localStorage.","sessionStorage.","gtag(","googletagmanager","facebook.net","fbq("):
            self.assertNotIn(pattern,code)
        self.assertIn("navigator.geolocation.getCurrentPosition",code)
        policy=(SITE/"privacy.html").read_text()
        for mandatory in ("Titolare del trattamento","Cookie e strumenti di tracciamento","Diritti",
                          "raw.githubusercontent.com","Wikimedia Commons","info@opera.plus"):
            self.assertIn(mandatory,policy)
        htaccess=(SITE/".htaccess").read_text()
        self.assertIn('Referrer-Policy "no-referrer"',htaccess)
        self.assertIn('Permissions-Policy "geolocation=(self)"',htaccess)

if __name__=="__main__":
    unittest.main()
