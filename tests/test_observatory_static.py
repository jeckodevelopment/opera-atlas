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

    def test_independent_year_and_season_filters(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        js = (ROOT / "observatory/app.js").read_text(encoding="utf-8")
        self.assertIn('id="year" aria-label="Anno solare"', html)
        self.assertIn('id="season" aria-label="Stagione teatrale"', html)
        self.assertIn('year:p.local_date.slice(0,4)', js)
        self.assertIn('year==="all"||r.year===year', js)
        self.assertIn('season==="all"||r.season===season', js)
        self.assertIn('["id","date","year","season"', js)
        self.assertIn('timeZone:"Europe/Rome"', js)

    def test_monthly_activity_and_compact_toolbar(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        js = (ROOT / "observatory/app.js").read_text(encoding="utf-8")
        css = (ROOT / "observatory/styles.css").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="download"'), 1)
        self.assertIn('class="header-export"', html)
        self.assertIn('Stagione <select id="season"', html)
        self.assertIn('id="months"', html)
        self.assertIn('Array(12).fill(0)', js)
        self.assertIn('drawMonths(selected,year)', js)
        self.assertIn('.toolbar{gap:12px;', css)

    def test_insights_use_canonical_ids_and_active_filters(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        js = (ROOT / "observatory/app.js").read_text(encoding="utf-8")
        css = (ROOT / "observatory/styles.css").read_text(encoding="utf-8")
        for identifier in ("weekday-chart", "venue-ranking", "diversity-chart",
                           "regional-works", "regional-composers", "staging-ranking"):
            self.assertIn('id="' + identifier + '"', html)
            self.assertIn('"' + identifier + '"', js)
        self.assertIn("renderInsights(selected)", js)
        self.assertIn("new Date(Date.UTC(y,m-1,d)).getUTCDay()", js)
        self.assertIn("r.venueId,r.venue", js)
        self.assertIn("r.stagingId,r.work", js)
        self.assertIn("diversity.get(row.region).add(row.workId)", js)
        self.assertIn("JSON.stringify([r.region,r.workId])", js)
        self.assertIn("JSON.stringify([r.region,r.composer])", js)
        self.assertIn(".insight-grid{display:grid;", css)
        self.assertNotIn("Prime e ultime date", html)

    def test_hero_photo_and_discreet_csv_action(self):
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        css = (ROOT / "observatory/styles.css").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="download"'), 1)
        self.assertIn('Esporta CSV</button>', html)
        self.assertNotIn('hero-credit', html)
        self.assertNotIn('Pasquale Matrisciano', html)
        self.assertIn("mockup-theatre-banner.svg", css)
        self.assertNotIn("InternoSanCarlo.JPG", css)
        self.assertIn(".top-inner .header-export{", css)
        self.assertIn("border-bottom:1px solid transparent", css)

    def test_world_premieres_and_repertoire_circulation(self):
        import json
        html = (ROOT / "observatory/index.html").read_text(encoding="utf-8")
        js = (ROOT / "observatory/app.js").read_text(encoding="utf-8")
        css = (ROOT / "observatory/styles.css").read_text(encoding="utf-8")
        for marker in ("premiere-total", "premiere-items", "circulation-rows"):
            self.assertIn('id="' + marker + '"', html)
        self.assertIn("function premieres(selected,year)", js)
        self.assertIn("function circulation(selected)", js)
        self.assertIn("h.premiere_year", js)
        self.assertIn("h.premiere_date", js)
        self.assertIn("work-editorial.json", js)
        self.assertIn("new Set(selected.map(r=>r.workId))", js)
        self.assertIn("g.venues.add(r.venueId)", js)
        self.assertIn("g.regions.add(r.region)", js)
        self.assertIn("g.cities.add(JSON.stringify([r.region,r.city]))", js)
        self.assertIn("year===\"all\"", js)
        self.assertIn("premieres(rows.filter(", js)
        self.assertIn("Stagione e territorio selezionano", js)
        self.assertIn(".feature-grid{display:grid;", css)
        self.assertNotIn("Prime e ultime date", html)
        editorial = json.loads((ROOT / "public/catalog/work-editorial.json").read_text(encoding="utf-8"))
        self.assertEqual(editorial["schema_version"], 1)
        self.assertTrue(any(w.get("history", {}).get("premiere_year") == 2026 for w in editorial["works"]))

    def test_logo_and_isolated_deployment(self):
        logo = (ROOT / "observatory/opera-plus-logo.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 250 117"', logo)
        self.assertIn('data:image/png;base64,', logo)
        deploy = (ROOT / "scripts/deploy_observatory_sftp.py").read_text(encoding="utf-8")
        self.assertIn('"opera-plus-logo.svg"', deploy)
        self.assertIn('"mockup-theatre-banner.svg"', deploy)
        self.assertIn('posixpath.join(posixpath.dirname(atlas), "osservatorio")', deploy)

if __name__ == "__main__":
    unittest.main()
