"""Shared authority-title resolution must use verified details, never URL guesses."""
import unittest
from scripts.auto_work_research import official_title_hint, research

URL="https://www.fondazionepetruzzelli.it/eventi/le-nozze-di-figaro-di-wolfgang-amadeus-mozart-12-19-settembre/"
CAND={"id":"source-independent-fixture","source_key":"petruzzelli-opera-2027",
      "official_url":URL,"status":"needs_review"}
def detail(*,title="Le nozze di Figaro",composer="Wolfgang Amadeus Mozart",
           source_url=URL,status="needs_editorial_review"):
    return {"candidate_id":CAND["id"],"source_key":CAND["source_key"],
            "source_url":source_url,"status":status,
            "event_facts":[{"event_title":title,"composer":composer,
                            "venue":"Teatro Petruzzelli",
                            "date":"2027-09-12","starts_at":"2027-09-12T20:30:00+02:00"}]}

class OfficialEvidenceTitleTests(unittest.TestCase):
    def test_uses_credited_title_not_slug_with_date_and_composer(self):
        evidence={"evidence":[detail()]}
        self.assertEqual(official_title_hint(CAND,evidence),"Le nozze di Figaro")
        self.assertNotEqual(official_title_hint(CAND,evidence),official_title_hint(CAND))

    def test_ambiguous_or_incomplete_detail_never_used_as_authority(self):
        e=detail()
        e["event_facts"].append({**e["event_facts"][0],"composer":"Another Composer"})
        self.assertIsNone(official_title_hint(CAND,{"evidence":[e]}))
        e=detail()
        del e["event_facts"][0]["starts_at"]
        self.assertIsNone(official_title_hint(CAND,{"evidence":[e]}))

    def test_wrong_source_pair_does_not_become_authority(self):
        e=detail(title="Fidelio",source_url=URL+"untrusted")
        self.assertNotEqual(official_title_hint(CAND,{"evidence":[e]}),"Fidelio")
        e=detail(title="Le lac des cygnes",status="needs_program_review")
        self.assertNotEqual(official_title_hint(CAND,{"evidence":[e]}),"Le lac des cygnes")

if __name__=="__main__":unittest.main()
