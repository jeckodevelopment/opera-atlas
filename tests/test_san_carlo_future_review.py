"""Future edition discovery does not extend an old publication attestation."""
from datetime import date
import unittest
from opera_atlas.controlled_fetch import FetchUnavailable
from scripts.discover_san_carlo_future import INDEX, SOURCE, discover, review_seasons
from scripts.scan_san_carlo_secondary import URL, parse, build_secondary_checkpoint
from scripts.corroborate_san_carlo_secondary import parse_independent
from scripts.apply_san_carlo_corroborated import apply

NEXT=URL.replace("2026-2027","2027-2028")
LATER=URL.replace("2026-2027","2028-2029")
TODAY=date(2026,11,28)
STAMP="2026-11-28T00:00:00Z"
INDEX_HTML=f'<a href="{URL}">Old</a><a href="{NEXT}">Future</a><a href="{LATER}">Later</a>'
CALENDAR="""<h1>Teatro di San Carlo</h1><p>Napoli</p>
<p>Giuseppe Verdi</p><h2>Rigoletto</h2><p>Teatro di San Carlo</p>
<h3>Recite</h3><p>Gio 2 Dicembre 2027 20:00</p>
<a href="https://www.teatrosancarlo.it/spettacoli/rigoletto/">BIGLIETTI</a>"""
INDEPENDENT="""<h1>Napoli - Teatro San Carlo</h1><h2>Stagione 2027/2028</h2>
<h4>RIGOLETTO</h4><h5>Dicembre 2027</h5><p>Dicembre: 02 (8h00 pm)</p>"""

class FutureReviewTests(unittest.TestCase):
    def test_only_exact_contiguous_future_season_links(self):
        html=INDEX_HTML+f'<a href="{NEXT}?ref=1">tracking</a><a href="{NEXT.replace("2028","2029")}">bad years</a><a href="{NEXT.replace("www.classicalive.it","example.org")}">external</a>'
        self.assertEqual(discover(html,today=TODAY),[NEXT])
        self.assertEqual(discover(INDEX_HTML,today=date(2028,1,1)),[NEXT,LATER])

    def test_comparison_does_not_authorize_publication(self):
        pages={INDEX:INDEX_HTML,NEXT:CALENDAR,SOURCE:INDEPENDENT}
        report=review_seasons(pages.__getitem__,today=TODAY,checked_at=STAMP)
        row=report["seasons"][0]
        self.assertEqual(row["status"],"awaiting_primary_repertoire")
        self.assertEqual(row["comparison"]["matching_recite_count"],1)
        self.assertFalse(row["comparison"]["canonical_publication_authorized"])
        self.assertFalse(report["canonical_publication_authorized"])
        with self.assertRaises(ValueError):
            apply(row["checkpoint"],row["comparison"],{"schema_version":1,"candidates":[]},
                  {"schema_version":1,"evidence":[]},checked_at=STAMP)

    def test_old_edition_and_future_out_of_range_are_rejected(self):
        with self.assertRaises(ValueError):
            parse(CALENDAR.replace("Gio 2 Dicembre 2027","Mer 2 Dicembre 2026"),url=NEXT)
        with self.assertRaises(ValueError):
            parse_independent(INDEPENDENT,season=(2026,2027))
        rows=parse(CALENDAR,url=NEXT)
        with self.assertRaises(ValueError):
            build_secondary_checkpoint(rows,checked_at=STAMP,incomplete=[])

    def test_absent_future_or_unavailable_source_is_not_empty_verified_calendar(self):
        report=review_seasons(lambda url:f'<a href="{URL}">Old</a>',today=TODAY,checked_at=STAMP)
        self.assertEqual(report["status"],"no_future_edition_verified")
        def fail(url):raise FetchUnavailable("temporary")
        self.assertEqual(review_seasons(fail,today=TODAY,checked_at=STAMP)["status"],"index_unavailable")
        pages={INDEX:INDEX_HTML,NEXT:CALENDAR,SOURCE:INDEPENDENT}
        prior=review_seasons(pages.__getitem__,today=TODAY,checked_at=STAMP)
        recovered=review_seasons(fail,today=TODAY,checked_at=STAMP,previous=prior)
        self.assertEqual(recovered["seasons"][0]["status"],"stale_index_unavailable")
        self.assertFalse(recovered["canonical_publication_authorized"])
