"""Wikimedia archive-first artwork discovery: no misidentified or restricted files."""
import unittest
from scripts.discover_wikimedia_art import (historical_candidate,find_historical_art,
                                           collect,commons_url)
from scripts.auto_catalogue import verified_candidate_image

TITLE="Il barbiere di Siviglia"
COMPOSER="Gioachino Rossini"
URL="https://www.fondazionepetruzzelli.it/eventi/il-barbiere-di-siviglia/"

def page(filename="Rossini Il barbiere di Siviglia original libretto 1816.jpg",
         artist="Original printer",license="Public domain",description="Rossini, Il barbiere di Siviglia: original libretto (1816)"):
    return {"title":"File:"+filename,"imageinfo":[{"extmetadata":{
        "Artist":{"value":artist},
        "LicenseShortName":{"value":license},
        "ImageDescription":{"value":description},
    }}]}

class WikimediaArtTests(unittest.TestCase):
    def test_historic_commons_file_requires_exact_work_and_composer(self):
        found=historical_candidate(page(),title=TITLE,composer=COMPOSER)
        self.assertEqual(found["kind"],"archival_work_image")
        self.assertIn("Rossini",found["source_url"])
        self.assertEqual(found["composer"],COMPOSER)
        self.assertEqual(found["license"],"Public domain (Commons declaration)")
        self.assertIsNone(historical_candidate(page(),title=TITLE,composer="Giovanni Paisiello"))
        self.assertIsNone(historical_candidate(page(license="Copyright"),title=TITLE,composer=COMPOSER))
        self.assertIsNone(historical_candidate(page(filename="Rossini portrait.jpg",
                description="Portrait of Rossini"),title=TITLE,composer=COMPOSER))
        self.assertIsNone(historical_candidate(page(filename="Rossini Il barbiere di Siviglia modern photo.jpg",
                description="Modern photo of performance"),title=TITLE,composer=COMPOSER))
        self.assertIsNone(commons_url("File:../../bad.jpg"))

    def test_same_identity_returns_stable_historical_file_without_guessing(self):
        calls=[]
        def fake(url):
            calls.append(url)
            return {"query":{"pages":[page()]}}
        art=find_historical_art(TITLE,COMPOSER,fetch=fake)
        self.assertEqual(len(calls),1)
        self.assertEqual(art["source_url"],"https://commons.wikimedia.org/wiki/File:Rossini_Il_barbiere_di_Siviglia_original_libretto_1816.jpg")
        self.assertEqual(verified_candidate_image(
            {"archival_poster_evidence":art},title=TITLE,url=URL,composer=COMPOSER)["kind"],
            "archival_work_image")
        self.assertIsNone(verified_candidate_image(
            {"archival_poster_evidence":art},title=TITLE,url=URL,composer="Giovanni Paisiello"))

    def test_archive_preferred_when_official_photo_also_exists(self):
        art=historical_candidate(page(),title=TITLE,composer=COMPOSER)
        detail={"archival_poster_evidence":art,"poster_evidence":{
            "kind":"official_production_image","image_url":"https://www.fondazionepetruzzelli.it/wp-content/uploads/il-barbiere-di-siviglia.jpg",
            "source_url":URL,"alt":"Official production","credit":"Theatre"}}
        chosen=verified_candidate_image(detail,title=TITLE,url=URL,composer=COMPOSER)
        self.assertEqual(chosen["kind"],"archival_work_image")
        self.assertNotIn("fondazionepetruzzelli.it",chosen["image_url"])

    def test_crawl_only_uncatalogued_compositions_with_verified_detail(self):
        known={"works":{}}
        intel={"works":[{"candidate_id":"c1","title":TITLE,"composer":COMPOSER}]}
        details={"evidence":[{"candidate_id":"c1","source_url":URL,
            "status":"needs_editorial_review","event_facts":[{"event_title":TITLE,
            "composer":COMPOSER}]}]}
        def fake(url):return {"query":{"pages":[page()]}}
        result,health=collect(intel,details,known,fetch=fake)
        self.assertEqual(len(result["art"]),1)
        self.assertEqual(health[0]["status"],"verified")
        self.assertEqual(result["art"][0]["candidate_id"],"c1")
        known["works"]={"a":{"title":TITLE,"composer":COMPOSER}}
        result,health=collect(intel,details,known,fetch=fake)
        self.assertEqual(result["art"],[])
        self.assertEqual(health,[])

if __name__=="__main__":
    unittest.main()
