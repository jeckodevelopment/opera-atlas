"""PDF report generator regression tests, including real Node execution."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ObservatoryPdfTests(unittest.TestCase):
    def test_wiring_and_deployment_scope(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts/deploy_observatory_sftp.py").read_text(encoding="utf-8")
        app = (ROOT / "observatory/app.js").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="report-pdf"'), 1)
        self.assertIn('src="./report-pdf.js"', html)
        self.assertIn('id="report-pdf" class="header-export pdf-export"', html)
        self.assertIn('"report-pdf.js"', deploy)
        self.assertIn('window.OperaPlusPdfReport.create(', app)
        self.assertIn('reviewedOn:catalogue.manifest.reviewed_on', app)
        self.assertIn('pdfButton.disabled=true', app)

    @unittest.skipUnless(shutil.which("node"), "Node required for PDF generation smoke test")
    def test_pdf_smoke(self):
        subprocess.run(
            ["node", "--check", "observatory/report-pdf.js"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        result = subprocess.run(
            ["node", "tests/observatory_pdf_smoke.cjs"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        self.assertIn("PDF smoke tests passed", result.stdout)
