"""Guardrails for the independent Observatory frontend and published identity."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ObservatoryStaticTests(unittest.TestCase):
    def test_official_brand_and_footer(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        self.assertIn('src="./opera-plus-logo.svg"', html)
        self.assertIn("<strong>Associazione Opera+</strong> · C.F. 97925160018", html)
        self.assertNotIn("Nessuna stima di pubblico", html)
        self.assertIn('href="https://opera.plus/"', html)
        self.assertIn('href="https://opera.plus/atlas/"', html)
        self.assertIn('href="https://opera.plus/osservatorio"', html)

    def test_compact_header_and_clean_stylesheet(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        css = (ROOT / "observatory/styles.css").read_text(encoding="utf-8")
        self.assertIn('alt="Opera+" width="94" height="44"', html)
        self.assertIn(".wordmark img{display:block;width:94px;", css)
        self.assertIn("html,body{margin:0;padding:0;background:#101c2b}", css)
        self.assertNotIn(r"\\n/* Marchio", css)

    def test_logo_and_isolated_deployment(self):
        logo = (ROOT / "observatory/opera-plus-logo.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 250 117"', logo)
        self.assertIn('data:image/png;base64,', logo)
        deploy = (ROOT / "scripts/deploy_observatory_sftp.py").read_text(encoding="utf-8")
        self.assertIn('"opera-plus-logo.svg"', deploy)
        self.assertIn('posixpath.join(posixpath.dirname(atlas), "osservatorio")', deploy)

if __name__ == "__main__":
    unittest.main()
