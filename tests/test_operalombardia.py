"""Date-only calendar statements from OperaLombardia are not timed events."""
import unittest

from opera_atlas.db import connect,migrate
from opera_atlas.operalombardia import parse_dates_only,stage_dates

URL="https://www.operalombardia.it/l-italiana-in-algeri/"
HTML="""<h1>L’italiana in Algeri</h1><h2>RECITE:</h2>
<p>Teatro Sociale, Como – 13 e 15 novembre 2026</p>
<p>Teatro Fraschini, Pavia – 20 e 22 novembre 2026</p>
<p>Teatro Grande, Brescia – 26 e 28 novembre 2026</p>
<p>Teatro Ponchielli, Cremona – 10 e 12 dicembre 2026</p>
<p>PRESTO ONLINE</p>"""


class OperaLombardiaTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        migrate(self.db)
        self.db.execute("INSERT INTO sources(official_url,access_status) VALUES "
                        "('https://www.operalombardia.it/','approved')")

    def tearDown(self):
        self.db.close()

    def test_four_venues_eight_date_only_records(self):
        result=parse_dates_only(HTML,url=URL,title="L’italiana in Algeri")
        self.assertEqual(len(result),8)
        self.assertEqual(result[0].local_date,"2026-11-13")
        self.assertEqual(result[-1].local_date,"2026-12-12")
        self.assertEqual(len(set(x.city for x in result)),4)

    def test_stage_idempotent_no_canonical_events(self):
        self.assertEqual(stage_dates(self.db,source_id=1,html=HTML,url=URL,
                                    title="L’italiana in Algeri"),8)
        self.assertEqual(stage_dates(self.db,source_id=1,html=HTML,url=URL,
                                    title="L’italiana in Algeri"),8)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM staged_recite").fetchone()[0],8)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0],0)

    def test_unapproved_source_rejected(self):
        self.db.execute("UPDATE sources SET access_status='pending'")
        with self.assertRaises(ValueError):
            stage_dates(self.db,source_id=1,html=HTML,url=URL,title="L’italiana in Algeri")

    def test_missing_date_section_does_not_guess(self):
        with self.assertRaises(ValueError):
            stage_dates(self.db,source_id=1,html="<h1>L’italiana in Algeri</h1>",
                        url=URL,title="L’italiana in Algeri")

    def test_reject_other_domain(self):
        with self.assertRaises(ValueError):
            parse_dates_only(HTML,url="https://example.org/foo",title="L’italiana in Algeri")

    def test_migration_repeat(self):
        migrate(self.db)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],7)


if __name__=="__main__":
    unittest.main()
