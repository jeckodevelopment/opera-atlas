"""Run the isolated Observatory Explore engine smoke test in standard CI."""
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
