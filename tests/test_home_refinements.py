"""Approved Atlas homepage counts, small dates, and festival visual hierarchy."""
import unittest
from pathlib import Path
import subprocess
import shutil

SITE=Path(__file__).resolve().parents[1]/"site"
class AtlasHomeRefinementTests(unittest.TestCase):
    def test_small_calendars_and_dynamic_count(self):
        js=(SITE/"app.js").read_text()
        css=(SITE/"styles.css").read_text()
        self.assertIn("function compactDate(event)",js)
        self.assertIn('node("div","home-calendar-list")',js)
        self.assertIn('const productionCount=groupByStaging(filtered).length;',js)
        self.assertIn('" in scena vicino a te"',js)
        self.assertIn(".home-calendar{width:53px",css)
        self.assertIn(".home-calendar-more",css)
    def test_festival_band_and_theatre_titles(self):
        css=(SITE/"styles.css").read_text()
        self.assertIn("#festival::before",css)
        self.assertIn("background:linear-gradient(115deg,#18242a",css)
        self.assertIn(".detail-related .theatre-production h3 a{font:inherit!important",css)
        self.assertIn(".detail-related .theatre-production .mini-calendar{min-height:68px",css)
        self.assertIn(".mini-calendar{appearance:none",css) # original production sizing intact
    def test_summary_fallback_and_home_discovery(self):
        home=(SITE/"app.js").read_text()
        directory=(SITE/"directory.js").read_text()
        self.assertIn("loadWorkDescriptions()",home)
        self.assertIn('workDescriptions[event.work_slug]||""',home)
        self.assertIn('node("span","discovery-description",description)',home)
        self.assertIn('https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/',directory)
    def test_curated_repertoire_is_in_requested_order(self):
        import re
        home=(SITE/"app.js").read_text(encoding="utf-8")
        block=home.split("const HOME_REPERTOIRE_IDS=Object.freeze([",1)[1].split("]);",1)[0]
        ids=re.findall(r'"(oa-w-\d{6})"',block)
        self.assertEqual(ids,[
            "oa-w-000026", # Rigoletto
            "oa-w-000015", # Aida
            "oa-w-000023", # Don Giovanni
            "oa-w-000031", # Norma
            "oa-w-000022", # Tosca
            "oa-w-000021"  # Lucia di Lammermoor
        ])
        self.assertIn("for(const id of HOME_REPERTOIRE_IDS)",home)
        self.assertNotIn("[...works].sort",home)

    def test_home_theatre_images_use_verified_venue_photos(self):
        import json
        home=(SITE/"app.js").read_text(encoding="utf-8")
        images=(SITE/"image-client.js").read_text(encoding="utf-8")
        registry=json.loads((SITE.parent/"data/venue-directory.json").read_text(encoding="utf-8"))
        carlo=next(v for v in registry["venues"] if v["city"]=="Genova" and v["slug"]=="teatro-carlo-felice")
        self.assertEqual(carlo["photo_file"],"Genova - Teatro Carlo Felice.jpg")
        self.assertIn("const homeVenueProfiles=new Map()",home)
        self.assertIn("const entries=await window.OperaAtlasCatalog.venues()",home)
        self.assertIn('const path of HOME_THEATRE_ROUTES',home)
        self.assertIn("photo_file:profile?.photo_file",home)
        self.assertIn("loadHomeVenueProfiles().catch",home)
        self.assertIn('city==="genova" && title==="Teatro Carlo Felice"',images)
        self.assertIn('"Genova - Teatro Carlo Felice.jpg"',images)
        self.assertIn("const verified=event?.photo_file || knownVenueFile;",images)

    def test_curated_home_theatres_have_requested_six_venues(self):
        import re,json
        home=(SITE/"app.js").read_text(encoding="utf-8")
        raw=home.split("const HOME_THEATRE_ROUTES=Object.freeze([",1)[1].split("]);",1)[0]
        routes=re.findall(r'"([a-z-]+/[a-z-]+)"',raw)
        self.assertEqual(routes,[
            "torino/teatro-regio","verona/arena-di-verona",
            "milano/teatro-alla-scala","genova/teatro-carlo-felice",
            "venezia/teatro-la-fenice","napoli/teatro-di-san-carlo"])
        self.assertNotIn("novara/teatro-coccia",routes)
        self.assertNotIn("ravenna/teatro-dante-alighieri",routes)
        self.assertIn("for(const path of HOME_THEATRE_ROUTES)",home)
        self.assertIn("const matching=[...venues].find",home)
        self.assertIn("const event=matching?.[1] || (profile ?",home)
        self.assertIn("window.OperaAtlasCatalog.urls(event).venue",home)
        directory=json.loads((SITE.parent/"data/venue-directory.json").read_text(encoding="utf-8"))
        records={v["city_slug"]+"/"+v["slug"]:v for v in directory["venues"]}
        for route in routes:
            self.assertIn(route,records)
            self.assertTrue(records[route].get("photo_file"),route)
            self.assertTrue(records[route].get("photo_source_url","").startswith("https://commons.wikimedia.org/"),route)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_distinct_archival_works_not_fictional_primary_poster(self):
        result=subprocess.run(["node",str(SITE.parent/"tests/image_client_smoke.cjs")],
          capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
if __name__=="__main__":
    unittest.main()
