"""Cagliari official index and date parser must fail closed."""
import json
import unittest
from pathlib import Path
from datetime import date
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

def sample_days(year=True):
    dates=[("ven","22/01","19:00"),("dom","24/01","17:00"),
           ("mar","26/01","19:00"),("gio","28/01","19:00"),
           ("sab","30/01","19:00")]
    return "".join("<p>ore "+clock+" "+weekday+" "+day+("/2027" if year else "")+
                   " turno</p>" for weekday,day,clock in dates)


class CagliariSourceTests(unittest.TestCase):
    def test_index_allowlist_and_config(self):
        document=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources=validate_config(document)
        source=next(x for x in sources if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,"https://www.liricocagliari.it/evento/parliamo-dopera-don-carlos/"))
        self.assertFalse(eligible(KEY,"https://www.liricocagliari.it/notizie/altro/"))
        self.assertEqual(len(sources),18)

    def test_index_excludes_other_hosts_and_talks(self):
        markup="<html>"+ "".join('<a href="/evento/%s/">opera</a>'%v for v in
            ["don-carlos","alcina","die-zauberflote","maria-stuarda",
             "la-boheme","candide","falstaff"]) + (
            '<a href="/evento/parliamo-dopera-don-carlos/">talk</a>'
            '<a href="https://example.invalid/evento/fake/">external</a></html>')
        found=extract(KEY,INDEX,markup,7)
        self.assertEqual(len(found),7)
        self.assertTrue(all(v.startswith("https://www.liricocagliari.it/evento/") for v in found))

    def test_explicit_year_and_clock_corrobated_with_brochure(self):
        source=html(sample_days(year=True))
        title,composer,venue,dates=parse_detail(source,url=DETAIL)
        self.assertEqual((title,composer,venue),("Don Carlos","Giuseppe Verdi","Teatro Lirico di Cagliari"))
        self.assertEqual(len(dates),5)
        self.assertEqual(dates[0],("2027-01-22","19:00"))
        self.assertEqual(dates[-1],("2027-01-30","19:00"))
        rows=parse_source_credited_opera_detail(KEY,DETAIL,source)
        self.assertEqual(rows[0]["starts_at"],"2027-01-22T19:00:00+01:00")
        self.assertEqual(len(rows),5)

    def test_yearless_days_corrobated_by_official_brochure(self):
        source=html(sample_days(year=False))
        _,_,_,dates=parse_detail(source,url=DETAIL)
        self.assertEqual(len(dates),5)
        self.assertEqual(dates[2],("2027-01-26","19:00"))

    def test_incomplete_and_changed_live_calendar_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_detail(html("<p>ore 19:00 ven 22/01 turno A</p>"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(html(sample_days().replace("19:00 ven 22/01","20:00 ven 22/01")),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(html(sample_days().replace("/2027","/2026")),url=DETAIL)

    def test_seven_individually_verified_operas_in_official_brochure(self):
        from opera_atlas.cagliari_detail_parser import BROCHURE
        evidence=json.loads(BROCHURE.read_text(encoding="utf-8"))
        self.assertEqual(len(evidence["works"]),7)
        self.assertEqual(sum(len(x["dates"]) for x in evidence["works"]),39)
        weekdays=["lun","mar","mer","gio","ven","sab","dom"]
        for work in evidence["works"]:
            rows="".join("<p>ore "+clock+" "+weekdays[date.fromisoformat(day).weekday()]+
                         " "+date.fromisoformat(day).strftime("%d/%m")+" turno</p>"
                         for day,clock in work["dates"])
            url="https://www.liricocagliari.it/evento/"+work["slug"]+"/"
            parsed=parse_detail(html(rows,title=work["title"],composer=work["composer"]),url=url)
            self.assertEqual(parsed[-1],[tuple(x) for x in work["dates"]])

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
