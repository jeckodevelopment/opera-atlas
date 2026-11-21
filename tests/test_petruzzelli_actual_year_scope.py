"""Petruzzelli season indexes must not re-date an older official production."""
import unittest
from opera_atlas.petruzzelli_detail_parser import official_petruzzelli_other_year
from scripts.reconcile_published_candidates import verified_other_season_evidence,reconcile

URL="https://www.fondazionepetruzzelli.it/eventi/la-notte-di-san-nicola-25-28-29-maggio/"
OLD="""<h1>LA NOTTE DI SAN NICOLA | 25-28-29 MAGGIO</h1>
<p>Opera per ragazzi di Nicola Campogrande</p>
<h2>Orari Spettacoli</h2>
<p>MERCOLEDÌ 25 MAGGIO 2022 - 18:30</p>
<p>SABATO 28 MAGGIO 2022 - 17:00</p>
<p>SABATO 28 MAGGIO 2022 - 18:30</p>
<p>DOMENICA 29 MAGGIO 2022 - 18:30</p>
<h2>La Trama</h2>"""

class PetruzzelliYearScope(unittest.TestCase):
    def test_old_2022_schedule_is_not_2027(self):
        self.assertEqual(official_petruzzelli_other_year(
            OLD,url=URL,season_year=2027),"2022")
        self.assertEqual(official_petruzzelli_other_year(
            OLD,url=URL,season_year=2026),"2022")
        self.assertIsNone(official_petruzzelli_other_year(
            OLD,url=URL,season_year=2022))
    def test_incomplete_ambiguous_and_wrong_weekday_fail_closed(self):
        self.assertIsNone(official_petruzzelli_other_year(
            OLD.replace("18:30","ore 18",1),url=URL,season_year=2027))
        self.assertIsNone(official_petruzzelli_other_year(
            OLD.replace("MERCOLEDÌ 25","GIOVEDÌ 25"),url=URL,season_year=2027))
        self.assertIsNone(official_petruzzelli_other_year(
            OLD.replace("2022 - 17:00","2027 - 17:00"),url=URL,season_year=2027))
        self.assertIsNone(official_petruzzelli_other_year(
            "<h1>2022</h1><p>O&B 2027</p>",url=URL,season_year=2027))
    def test_hashed_source_scoped_evidence_retires_only_misindexed_candidate(self):
        row={"candidate_id":"candidate-old","source_key":"petruzzelli-opera-2027",
             "source_url":URL,"status":"out_of_monitored_season",
             "official_season":"2022","content_sha256":"a"*64}
        approved=verified_other_season_evidence({"evidence":[row]})
        self.assertEqual(approved,{("petruzzelli-opera-2027",URL)})
        pending={"schema_version":1,"candidates":[
            {"id":"candidate-old","source_key":"petruzzelli-opera-2027",
             "official_url":URL,"status":"needs_review"}]}
        out,report=reconcile(pending,set(),other_season_urls=approved)
        self.assertEqual(out["candidates"][0]["status"],"not_in_official_season")
        self.assertEqual(len(report["changes"]),1)
        self.assertFalse(verified_other_season_evidence({"evidence":[
            {**row,"content_sha256":"not-a-sha"}]}))
        self.assertFalse(verified_other_season_evidence({"evidence":[
            {**row,"official_season":"2027"}]}))
        self.assertFalse(verified_other_season_evidence({"evidence":[
            {**row,"source_key":"petruzzelli-opera-2026","official_season":"2026"}]}))

if __name__=="__main__":
    unittest.main()
