"""Run Explore smoke tests in standard CI and guard the isolated page."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ObservatoryExploreTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_engine(self):
        subprocess.run(["node", "tests/observatory_explore_engine.cjs"],
                       cwd=ROOT, check=True, timeout=30)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_ui_helpers_and_catalog(self):
        for script in ("engine.js", "data.js", "analysis.js", "export.js", "report.js", "explore.js"):
            subprocess.run(["node", "--check", "observatory-explore/" + script],
                           cwd=ROOT, check=True, timeout=30)
        subprocess.run(["node", "tests/observatory_explore_ui.cjs"],
                       cwd=ROOT, check=True, timeout=30)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_analysis(self):
        subprocess.run(["node", "tests/observatory_explore_analysis.cjs"],
                       cwd=ROOT, check=True, timeout=30)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_exports(self):
        subprocess.run(["node", "tests/observatory_explore_export.cjs"],
                       cwd=ROOT, check=True, timeout=30)

    def test_isolated_page(self):
        html = (ROOT / "observatory-explore/index.html").read_text(encoding="utf-8")
        for marker in ('href="../styles.css"', 'src="../opera-plus-logo.svg"',
                       'src="/atlas/catalog-client.js"', 'id="query"', 'id="metrics"',
                       'id="detail-table"', 'id="view"', 'id="explore-content" hidden',
                       'id="preset"', 'id="group-by"', 'id="group-metric"',
                       'id="monthly-chart"', 'id="region-chart"', 'id="comparison-chart"',
                       'id="group-body"', 'src="./analysis.js"',
                       'id="export-pdf"', 'id="export-summary"', 'id="export-detail"', 'id="share-query"',
                       'rel="canonical" href="https://opera.plus/osservatorio/esplora/"'):
            self.assertIn(marker, html)
        self.assertNotIn("observatory-explore", (ROOT / "observatory/index.html").read_text(encoding="utf-8"))
