"""Cagliari official index and date parser must fail closed."""
import json
import unittest
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_source_credited_opera_detail
from opera_atlas.cagliari_detail_parser import parse_detail

KEY="lirico-cagliari-opera-2027"
INDEX="https://www.liricocagliari.it/categoria-evento/opera/"
DETAIL="https://www.liricocagliari.it/evento/don-carlos/"

def html(dates, title="Don Carlos", composer="Giuseppe Verdi", extra_heading=False):
    return (
        "<html><nav><h2>Opera</h2><h2>Stagione 2027</h2></nav>"
        "<main><h1>"+title+"</h1><h2>"+composer+"</h2>"
        "<div>5 spettacoli</div><h3>Date</h3><a>vedi tutto</a>"
        "<span>ore 20:00 merc 24/06</span>"
        +dates+
        "<h3>Personaggi e interpreti</h3><p>Cast: 23/01</p>"
        "</main>"+("<aside><h1>Other work</h1></aside>" if extra_heading else "")+"</html>"
    )

class CagliariSourceTests(unittest.TestCase):
    def test_index_allowlist_and_config(self):
        document=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources=validate_config(document)
        source=next(x for x in sources if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,"https://www.liricocagliari.it/evento/parliamo-dopera-don-carlos/"))
        self.assertFalse(eligible(KEY,"https://www.liricocagliari.it/notizie/altro/"))
        self.assertEqual(len(sources),16)

    def test_index_excludes_other_hosts_and_talks(self):
        markup="<html>"+ "".join('<a href="/evento/%s/">opera</a>'%v for v in
            ["don-carlos","alcina","die-zauberflote","maria-stuarda",
             "la-boheme","candide","falstaff"]) + (
            '<a href="/evento/parliamo-dopera-don-carlos/">talk</a>'
            '<a href="https://example.invalid/evento/fake/">external</a></html>')
        found=extract(KEY,INDEX,markup,7)
        self.assertEqual(len(found),7)
        self.assertTrue(all(v.startswith("https://www.liricocagliari.it/evento/") for v in found))

    def test_explicit_year_and_clock_are_required(self):
        source=html("<p>ore 19:00 ven 22/01/2027 turno A</p>"
                    "<p>ore 17:00 dom 24/01/2027 turno D</p>")
        title,composer,venue,dates=parse_detail(source,url=DETAIL)
        self.assertEqual((title,composer,venue),("Don Carlos","Giuseppe Verdi","Teatro Lirico di Cagliari"))
        self.assertEqual(dates,[("2027-01-22","19:00"),("2027-01-24","17:00")])
        rows=parse_source_credited_opera_detail(KEY,DETAIL,source)
        self.assertEqual(rows[0]["starts_at"],"2027-01-22T19:00:00+01:00")
        self.assertEqual(len(rows),2)

    def test_no_year_no_publication(self):
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01 turno A</p>"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01/2026 turno A</p>"),url=DETAIL)

    def test_invalid_host_and_nonopera_and_cancellation(self):
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01/2027</p>"),
                url=DETAIL.replace("www.liricocagliari.it","example.invalid"))
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01/2027 ANNULLATA</p>"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01/2027</p>",
                              title="Parliamo d'opera: Don Carlos",composer="incontro d'approfondimento"),url=DETAIL)

    def test_ambiguous_other_work_heading_rejected(self):
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01/2027</p>",extra_heading=True),url=DETAIL)

if __name__=="__main__":
    unittest.main()
