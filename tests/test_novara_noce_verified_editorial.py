"""The Noce di Benevento authority and official title-specific art are sourced."""
import json
import unittest
from pathlib import Path
from scripts.auto_catalogue import official_identity_candidates,verified_candidate_image
from scripts.build_verified_catalog import official_local_time
from scripts.publish_work_posters import extract_official_poster
from scripts.publish_work_editorial import validate_history

URL="https://www.fondazioneteatrococcia.it/stagione-27-il-noce-di-benevento.html"
IMAGE="https://www.fondazioneteatrococcia.it/images/spettacoli/stagione-27/1920x950_IL_NOCE_DI_BENEVENTO.png"
SOURCE="coccia-novara-rolling-opera"

def candidate():
    return {"schema_version":1,"candidates":[{"id":"noce-test","source_key":SOURCE,
                "official_url":URL,"status":"needs_review"}]}

def detail():
    return {"schema_version":1,"evidence":[{
        "candidate_id":"noce-test","source_key":SOURCE,"source_url":URL,
        "status":"needs_editorial_review","event_facts":[
            {"event_title":"IL NOCE DI BENEVENTO","composer":"Giuseppe Balducci",
             "venue":"Giardini di Palazzo Natta","date":day,
             "starts_at":official_local_time(day,"21:00")}
            for day in ("2027-06-17","2027-06-18")]}]}

class NoceOfficialEditorialTests(unittest.TestCase):
    def test_complete_source_bound_history_and_plot(self):
        seed=next(x for x in json.loads(Path(
            "data/verified-work-authority-seeds.json").read_text())["works"]
            if x["source_url"]==URL)
        self.assertEqual(seed["title"],"Il noce di Benevento")
        self.assertEqual(seed["composer"],"Giuseppe Balducci")
        self.assertTrue(validate_history(seed["history"]))
        self.assertGreaterEqual(len(seed["synopsis"]),45)
        self.assertLessEqual(len(seed["synopsis"]),300)
        doc=official_identity_candidates(detail(),candidate(),
                                         {"schema_version":1,"works":[]})
        self.assertEqual(len(doc["works"]),1)
        self.assertEqual(doc["works"][0]["title"],seed["title"])
        self.assertEqual(doc["works"][0]["history"],seed["history"])
        self.assertEqual(doc["works"][0]["synopsis"],seed["synopsis"])

    def test_only_unique_first_party_work_image_near_h1(self):
        html=(
            "<nav><img src='/logo.png'/></nav>"
            "<h1>IL NOCE DI BENEVENTO</h1>"
            f"<img src='{IMAGE}' alt='Il noce di Benevento'/>"
            "<h3>informazioni sull'evento</h3>"
            "<footer><img src='/images/other-opera.png'/></footer>")
        image=extract_official_poster(html,URL,"Il noce di Benevento")
        self.assertEqual(image["image_url"],IMAGE)
        record=detail()["evidence"][0]
        record["poster_evidence"]=image
        self.assertEqual(verified_candidate_image(record,title="Il noce di Benevento",
            composer="Giuseppe Balducci",url=URL)["image_url"],IMAGE)
        for invalid in (
            html.replace(IMAGE,"/images/spettacoli/stagione-27/generic-season.png"),
            html.replace(IMAGE,"https://other.example/IL_NOCE_DI_BENEVENTO.png"),
            html.replace("<h3>informazioni sull'evento</h3>",
                         "<img src='/images/spettacoli/stagione-27/ALT_IL_NOCE_DI_BENEVENTO.png'/>"
                         "<h3>informazioni sull'evento</h3>"),
            html.replace("<h1>IL NOCE DI BENEVENTO</h1>","<h2>Opera</h2>"),
        ):
            with self.subTest(case=invalid[-110:]):
                self.assertIsNone(extract_official_poster(
                    invalid,URL,"Il noce di Benevento"))

if __name__=="__main__":
    unittest.main()
