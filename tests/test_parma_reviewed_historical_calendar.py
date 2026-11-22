"""Exact reviewed first-party source keeps family ticketing separate from schools."""
import unittest
from opera_atlas.parma_reviewed_historical_calendar import (
    SOURCE_KEY,URL,TITLE,REVIEWED_PUBLIC,EXCLUDED_SCHOOLS,verified_calendar)
from tests.test_parma_family_opera import page

class ParmaReviewedHistoricalCalendarTests(unittest.TestCase):
    def test_public_dates_only_when_exact_first_party_identity_matches(self):
        observed=verified_calendar(page(),source_key=SOURCE_KEY,url=URL)
        self.assertEqual([(x["date"],x["starts_at"][11:16]) for x in observed],
                         list(REVIEWED_PUBLIC))
        self.assertFalse(any(x["date"]==day and x["starts_at"][11:16]==time
                             for x in observed for day,time in EXCLUDED_SCHOOLS))
        for url in (URL+"?preview=1","https://elsewhere.example/production/"):
            with self.assertRaises(ValueError):
                verified_calendar(page(),source_key=SOURCE_KEY,url=url)
        for broken in (page().replace(TITLE,"Other opera"),
                       page().replace("musica Giovanni Sollima","musica Other author"),
                       page().replace("5 dic 2026","5 dic 2028"),
                       page().replace("Teatro Regio di Parma","Another venue"),
                       page()+"<p>Annullato</p>"):
            with self.subTest(broken=broken[-80:]),self.assertRaises(ValueError):
                verified_calendar(broken,source_key=SOURCE_KEY,url=URL)

    def test_live_ticket_markup_changes_do_not_invent_school_recite(self):
        # The two approved public times are historical first-party facts;
        # no current CMS display format is needed for their identity.
        html=page().replace("<div>sab 5 dic</div><div>15:00</div>",
                           "<section>biglietti in archivio</section>")
        facts=verified_calendar(html,source_key=SOURCE_KEY,url=URL)
        self.assertEqual(len(facts),2)
        self.assertTrue(all(f["date"]=="2026-12-05" for f in facts))

if __name__=="__main__":
    unittest.main()
