"""Five Ferrara operas and ten recite verified from official season sources."""
import json
import unittest
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
    def test_five_approved_index_keys_and_distinct_work_evidence(self):
        document=json.loads(CONFIG.read_text(encoding="utf-8"))
        src=validate_config(document)
        self.assertEqual(len(src),26)
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
            self.assertIn("+01:00",facts[0]["starts_at"])

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
        # A shared official season URL is not a shared opera identity.
        for key in KEYS:
            self.assertEqual(classify(key,URL,set([URL])),
                             "needs_review")

if __name__=="__main__":
    unittest.main()
