"""Five Ferrara operas and ten recite verified from official season sources."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import date
from opera_atlas.ferrara_regional_parser import REGISTRY,production,records,verified_index_candidate
from scripts.discover_season_indexes import CONFIG,extract,eligible,validate_config
from scripts.collect_candidate_details import parse_source_credited_opera_detail
from scripts.discover_season_indexes import classify

URL="https://spettacolo.emiliaromagnacultura.it/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"
KEYS=["ferrara-"+x+"-opera-2026-27" for x in ("macbeth","barbiere","dido","clemenza","boccanegra")]
EXPECTED={
    "macbeth":[("2026-11-27","20:00"),("2026-11-29","16:00")],
    "barbiere":[("2027-01-15","20:00"),("2027-01-17","16:00")],
    "dido":[("2027-02-20","20:00"),("2027-02-21","16:00")],
    "clemenza":[("2027-03-12","20:00"),("2027-03-14","16:00")],
    "boccanegra":[("2027-04-09","20:00"),("2027-04-11","16:00")]
}

def regional_html():
    from opera_atlas.ferrara_regional_parser import records
    rows=records()
    html='<html><h1>TEATRO COMUNALE FERRARA - OPERA &amp; DANZA 2026/2027</h1>'
    html+='<h3>ROMEO E GIULIETTA</h3><p>30 Dicembre 2026 - 31 Dicembre 2026'
    html+=' Ferrara - TEATRO COMUNALE DI FERRARA. Balletto.</p>'
    for key in KEYS:
        rec=rows[key]
        heading=rec["title"].upper()+(" - "+rec["composer"] if key==KEYS[0] else "")
        html+='<h3>'+heading+'</h3><p>musica di '+rec["composer"]
        html+=' - Nell ambito di: TEATRO COMUNALE FERRARA - OPERA &amp; DANZA 2026/2027'
        html+=' - '+rec["span"][0]+' - '+rec["span"][1]
        html+=' Ferrara (FE Ferrara) - TEATRO COMUNALE DI FERRARA</p>'
    html+='<h3>MOMO</h3><p>19 Maggio 2027 Ferrara - danza Batsheva</p>'
    html+='</html>'
    return html

class FerraraOfficialSourceTests(unittest.TestCase):
    def test_independent_tourism_fallback_preserves_canonical_candidates(self):
        from opera_atlas.ferrara_regional_parser import TOURISM_URL,verify_tourism_calendar
        from opera_atlas.controlled_fetch import FetchUnavailable,FetchResult,AccessDenied
        from scripts.discover_season_indexes import scan
        from scripts.build_verified_catalog import MANIFEST
        from datetime import date
        months={11:"novembre",1:"gennaio",2:"febbraio",3:"marzo",4:"aprile"}
        body="<h1>Stagione Opera &amp; Danza - Teatro Comunale Ferrara 2026 2027</h1>"
        for row in records().values():
            for day,clock in row["dates"]:
                d=date.fromisoformat(day)
                body+=f"<p>{d.day} {months[d.month]} ore {clock}</p>"
            body+=f'<h2>{row["title"]}</h2><p>Musica di {row["composer"]}</p>'
        for key in KEYS:
            verify_tourism_calendar(body,url=TOURISM_URL,source_key=key)
        with self.assertRaises(ValueError):
            verify_tourism_calendar(body.replace("27 novembre ore 20:00","27 novembre ore 21:00"),
                                    url=TOURISM_URL,source_key=KEYS[0])
        config=json.loads(CONFIG.read_text())
        requests=[]
        def fetch(db,*,source_id,url,network_enabled):
            requests.append(url)
            if url==URL: raise FetchUnavailable("page unavailable")
            if url==TOURISM_URL: return FetchResult(url,body,"a"*64,len(body))
            raise AssertionError(url)
        candidates,health=scan(config,{"schema_version":1,"candidates":[]},
                               fetcher=fetch,network_enabled=True,source_keys=set(KEYS))
        self.assertEqual(len(health),5)
        self.assertTrue(all(x["status"]=="success" and x["fallback_official_source"]=="www.ferrarainfo.com" for x in health))
        self.assertTrue(all(x["status"]=="already_catalogued" and x["official_url"]==URL for x in candidates["candidates"]))
        self.assertEqual(len(candidates["candidates"]),5)
        def denied(db,*,source_id,url,network_enabled):
            self.assertEqual(url,URL)
            raise AccessDenied("robots denied")
        _,health=scan(config,{"schema_version":1,"candidates":[]},
                      fetcher=denied,network_enabled=True,source_keys={KEYS[0]})
        self.assertEqual(health[0]["status"],"unavailable_or_invalid")

    def test_five_approved_index_keys_and_distinct_work_evidence(self):
        document=json.loads(CONFIG.read_text(encoding="utf-8"))
        src=validate_config(document)
        configured=[x for x in src if x["key"] in KEYS]
        self.assertEqual(len(configured),5)
        self.assertTrue(all(x["url"]==URL for x in configured))
        self.assertEqual(sum(len(x["dates"]) for x in records().values()),10)
        self.assertTrue(eligible(KEYS[0],URL))
        self.assertFalse(eligible(KEYS[0],"https://spettacolo.emiliaromagnacultura.it/it/luogo/teatro-comunale-claudio-abbado/"))

    def test_each_regional_index_discovers_just_its_own_official_candidate(self):
        markup=regional_html()
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(extract(key,URL,markup,1),[URL])
                self.assertTrue(verified_index_candidate(markup,source_key=key,url=URL))

    def test_all_ten_productions_at_one_canonical_ferrara_venue(self):
        markup=regional_html()
        for key in KEYS:
            suffix=key.removeprefix("ferrara-").removesuffix("-opera-2026-27")
            title,composer,venue,dates=production(markup,source_key=key,url=URL)
            self.assertEqual(venue,"Teatro Comunale Claudio Abbado")
            self.assertEqual(dates,EXPECTED[suffix])
            facts=parse_source_credited_opera_detail(key,URL,markup)
            self.assertEqual(len(facts),2)
            self.assertEqual(facts[0]["date"],dates[0][0])
            self.assertEqual(facts[0]["venue"],venue)
            self.assertEqual(facts[0]["composer"],composer)
            expected_offset="+01:00" if dates[0][0]<"2027-03-28" else "+02:00"
            self.assertTrue(facts[0]["starts_at"].endswith(expected_offset))

    def test_no_dance_or_unverified_dates_enter_catalogue(self):
        for key in KEYS:
            markup=regional_html()
            entry=records()[key]
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    production(markup.replace(entry["span"][0],"10 Agosto 2030"),
                               source_key=key,url=URL)
                with self.assertRaises(ValueError):
                    production(markup,url=URL.replace("spettacolo.emiliaromagnacultura.it","untrusted.invalid"),source_key=key)

    def test_one_published_work_does_not_close_the_other_four(self):
        # Use a controlled snapshot: the live catalog may already contain
        # some or all of these works, unlike this deliberately partial fixture.
        macbeth = records()[KEYS[0]]
        fixture = {"productions": [{
            "title": macbeth["title"],
            "composer": macbeth["composer"],
            "municipality": "Ferrara",
            "venue": "Teatro Comunale Claudio Abbado",
            "source_url": URL,
        }]}
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "catalog.json"
            manifest.write_text(json.dumps(fixture), encoding="utf-8")
            with patch("scripts.build_verified_catalog.MANIFEST", manifest):
                self.assertEqual(classify(KEYS[0], URL, {URL}), "already_catalogued")
                for key in KEYS[1:]:
                    self.assertEqual(classify(key, URL, {URL}), "needs_review")

if __name__=="__main__":
    unittest.main()
