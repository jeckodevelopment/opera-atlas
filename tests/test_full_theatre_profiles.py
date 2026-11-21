"""Full sourced theatre profile regressions and no placeholder output."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from scripts.publish_venue_directory import SOURCE, OUTPUT, publish

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class FullTheatreProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=json.loads(SOURCE.read_text(encoding="utf-8"))["venues"]
        cls.profiles=json.loads((SITE/"theatre-profiles.json").read_text(encoding="utf-8"))["venues"]

    def test_all_fifty_two_have_real_profiles_and_map_addresses(self):
        self.assertEqual(len(self.directory),52)
        self.assertEqual(len(self.profiles),52)
        for venue in self.directory:
            key=venue.get("profile_key",venue["city"]+"|"+venue["name"])
            self.assertIn(key,self.profiles,key)
            profile=self.profiles[key]
            self.assertTrue(profile["address"].strip(),key)
            self.assertGreaterEqual(len(profile["history"].strip()),80,key)
            self.assertTrue(profile["source"].startswith("https://"),key)
            self.assertEqual(profile["address"],venue["address"],key)
            self.assertEqual(profile["history"],venue["history"],key)
            self.assertEqual(profile["description"],venue["description"],key)
            # A short introduction must not duplicate the historical text.
            # This prevents the previous 26 exact duplicates from returning.
            short=re.sub(r"\\W+"," ",venue["description"].casefold()).strip()
            history=re.sub(r"\\W+"," ",venue["history"].casefold()).strip()
            self.assertNotEqual(short,history,key)
            self.assertLessEqual(len(venue["description"]),260,key)
        published=publish(check=True)["venues"]
        self.assertEqual({v["id"] for v in published},
                         {v["id"] for v in self.directory})
        by_id={v["id"]:v for v in published}
        for source in self.directory:
            # A newly ingested opera may promote an already censused venue
            # without changing any editorial address, photo or history.
            published_venue=by_id[source["id"]]
            for field in ("slug","city_slug","description","address","history","photo_file"):
                self.assertEqual(published_venue.get(field),source.get(field))
            if published_venue.get("canonical_venue_id")!=source.get("canonical_venue_id"):
                self.assertEqual(published_venue["calendar_status"],"acquired")

    def test_all_active_venues_have_individual_illustrations_and_credits(self):
        photos=[v for v in self.directory if v.get("photo_file")]
        self.assertEqual(len(photos),50)
        external=[v for v in self.directory if v.get("photo_url")]
        self.assertEqual([v["name"] for v in external],["Teatro Politeama Greco"])
        self.assertEqual(external[0]["photo_license"],"CC BY 4.0")
        for venue in photos:
            self.assertTrue(venue["photo_source_url"].startswith(
                "https://commons.wikimedia.org/wiki/File:"),venue["id"])
            self.assertTrue(venue.get("photo_credit"),venue["id"])
        without=[v for v in self.directory if not v.get("photo_file")]
        self.assertEqual({v["name"] for v in without},
                         {"Teatro Comunale Nouveau","Teatro Politeama Greco"})
        self.assertEqual(next(v["photo_status"] for v in without if v["name"]=="Teatro Politeama Greco"),
                         "verified")
        self.assertNotEqual(next(v["photo_file"] for v in photos if v["name"]=="Arena di Verona"),
                            next(v["photo_file"] for v in photos if v["name"]=="Teatro Filarmonico"))

    def test_no_unfinished_placeholder_and_theatre_detail_has_photo_history_map(self):
        detail=(SITE/"detail.js").read_text(encoding="utf-8")
        directory=(SITE/"directory.js").read_text(encoding="utf-8")
        for content in (detail,directory):
            self.assertNotIn("La sede è censita. Il programma degli spettacoli non è ancora stato acquisito.",content)
            if content==directory:
                self.assertNotIn("Calendario non ancora acquisito",content)
        self.assertIn('node("section","theatre-history")',detail)
        self.assertIn('link("Come arrivare"',detail)
        self.assertIn("openstreetmap.org/search",detail)
        self.assertIn('const venueImageEvent=',detail)
        self.assertIn('photo_file:item.photo_file',directory)
        self.assertIn('photo_url:item.photo_url',directory)
        self.assertIn('photo_file:venue.photo_file',directory)
        self.assertIn('photo_url:venue.photo_url',directory)
        script=(SITE/"image-client.js").read_text(encoding="utf-8")
        self.assertIn("event?.photo_file",script)
        self.assertIn('const verified=event?.photo_file || knownVenueFile;',script)
        venue_code=script.split("  function venue(event){",1)[1].split("  function festival(event){",1)[0]
        self.assertIn("VENUE_NAMES[city]?.includes(title)",venue_code)
        self.assertIn('const file=typeof verified===',venue_code)
        self.assertIn('selected.venue?.calendar_status==="acquired"',detail)
        self.assertIn("Calendario non ancora acquisito · consulta il ",detail)
        self.assertIn("Non risultano prossimi spettacoli in programma.",detail)
        for text in ("sede teatrale censita","Le rappresentazioni saranno collegate"):
            for venue in self.directory:self.assertNotIn(text,venue["description"])

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_javascript_is_syntactically_valid(self):
        for name in ("detail.js","directory.js","image-client.js"):
            result=subprocess.run(["node","--check",str(SITE/name)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,name+" "+result.stderr)

if __name__=="__main__":
    unittest.main()
