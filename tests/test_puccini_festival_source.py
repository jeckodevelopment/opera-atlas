"""2027 Puccini festival: official recite and composite-bill quarantine."""
import json
import unittest
from datetime import date

from opera_atlas.puccini_festival_parser import parse_program,URL,KEY
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.publish_catalog_v2 import REGISTRY
from scripts.auto_catalogue import split_verified_season,promote
from scripts.build_verified_catalog import MANIFEST
from scripts.rollover_season_indexes import next_index

PROGRAMME="""<h1>73rd Puccini Festival</h1>
<h2>2027 programme</h2>
<p>9 July – 29 August 2027</p>
<p>Giacomo Puccini Open-Air Theatre</p>
<p>All performances start at 9.15 pm</p>
<h2>The operas</h2>
<p>9 July · 22 August</p><h3>La rondine</h3>
<p>Celebrating 110 years since the world premiere</p>
<a>Explore the opera and cast</a>
<p>10, 23 and 31 July · 13 and 28 August</p><h3>Turandot</h3>
<a>Explore the opera and cast</a>
<p>16 and 24 July · 6 and 21 August</p><h3>Tosca</h3>
<a>Explore the opera and cast</a>
<p>25 July · 29 August</p><h3>Il Trittico</h3>
<p>Il tabarro · Suor Angelica · Gianni Schicchi</p>
<a>Explore the opera and cast</a>
<p>30 July · 8 and 20 August</p><h3>Madama Butterfly</h3>
<a>Explore the opera and cast</a>
<p>7, 14 and 27 August</p><h3>La bohème</h3>
<a>Explore the opera and cast</a>
<h2>The concerts</h2>
<p>11 July 2027</p><h3>A tribute to Italian opera</h3>"""

class PucciniOfficialCalendarTests(unittest.TestCase):
    def test_strict_source_and_15_consistent_recite(self):
        sources=validate_config(json.loads(CONFIG.read_text()))
        self.assertIn(KEY,[s["key"] for s in sources])
        self.assertTrue(eligible(KEY,URL))
        self.assertEqual(extract(KEY,URL,PROGRAMME,1),[URL])
        found=parse_program(PROGRAMME,url=URL)
        self.assertEqual(len(found),15)
        counts={title:sum(item[0]==title for item in found)
                for title in {x[0] for x in found}}
        self.assertEqual(counts,{
            "Turandot":5,"Tosca":4,"Madama Butterfly":3,"La bohème":3})
        self.assertEqual({r[2] for r in found},{"Gran Teatro Giacomo Puccini"})
        self.assertEqual({r[4] for r in found},{"21:15"})
        self.assertEqual(found[0][-2:],("2027-07-10","21:15"))
        self.assertEqual(found[-1][-2:],("2027-08-27","21:15"))

    def test_homepage_conflicting_rondine_and_composite_not_auto_published(self):
        found=parse_program(PROGRAMME,url=URL)
        self.assertNotIn("La rondine",{x[0] for x in found})
        self.assertNotIn("Il Trittico",{x[0] for x in found})
        self.assertFalse(any(x[0] in ("Il tabarro","Suor Angelica","Gianni Schicchi")
                             for x in found))
        for corrupt in (
            PROGRAMME.replace("Giacomo Puccini Open-Air Theatre","Teatro Comunale"),
            PROGRAMME.replace("All performances start at 9.15 pm","Shows begin at various times"),
            PROGRAMME.replace("13 and 28 August","13 August"),
            PROGRAMME.replace("Il tabarro · Suor Angelica · Gianni Schicchi",
                               "Il tabarro · Gianni Schicchi"),
            PROGRAMME.replace("2027 programme","2026 programme"),
        ):
            with self.subTest(corrupt=corrupt[:80]),self.assertRaises(ValueError):
                parse_program(corrupt,url=URL)
        for url in (URL+"?ref=test",URL.replace("https://","http://"),
                    URL.replace("puccinifestival.it","example.invalid")):
            with self.assertRaises(ValueError):parse_program(PROGRAMME,url=url)

    def test_canonical_work_identity_and_composite_safe_split(self):
        registry=json.loads(REGISTRY.read_text())
        facts=parse_known_opera_detail(KEY,URL,PROGRAMME,registry)
        self.assertEqual(len(facts),15)
        self.assertEqual({x["composer"] for x in facts},{"Giacomo Puccini"})
        item={"candidate_id":"puccini-test","source_key":KEY,"source_url":URL,
              "status":"needs_editorial_review","event_facts":facts}
        groups=split_verified_season(item)
        self.assertEqual(len(groups),4)
        self.assertEqual(sorted(len(x["event_facts"]) for x in groups),[3,3,4,5])

    def test_future_edition_requires_verified_programme(self):
        sources=validate_config(json.loads(CONFIG.read_text()))
        current=next(x for x in sources if x["key"]==KEY)
        self.assertIsNone(next_index(current,today=date(2027,8,31)))
        future=next_index(current,today=date(2027,9,1))
        self.assertEqual(future,
            "https://www.puccinifestival.it/en/74th-puccini-festival-2028/")
        self.assertTrue(eligible(KEY,future))
        self.assertFalse(eligible(KEY,
            "https://www.puccinifestival.it/en/75th-puccini-festival-2028/"))
        next_year=dict(current,url=future)
        self.assertEqual(next_index(next_year,today=date(2028,9,1)),
            "https://www.puccinifestival.it/en/75th-puccini-festival-2029/")
        future_page=PROGRAMME.replace("73rd","74th").replace("2027","2028")
        self.assertEqual(len(parse_program(future_page,url=future)),15)
        with self.assertRaises(ValueError):
            parse_program(PROGRAMME,url=future)

    def test_future_changed_repertoire_and_clock(self):
        url=URL.replace("73rd","74th").replace("2027","2028")
        page=PROGRAMME.split('<h2>The operas</h2>')[0].replace("73rd","74th").replace("2027","2028").replace("9.15 pm","8.30 pm")
        page += '<h2>The operas</h2><p>12 July</p><h3>Manon Lescaut</h3><a>Explore the opera and cast</a><h2>The concerts</h2>'
        self.assertEqual(parse_program(page,url=url),[("Manon Lescaut","Giacomo Puccini","Gran Teatro Giacomo Puccini","2028-07-12","20:30")])
        self.assertEqual(extract(KEY,url,page,1),[url])
        with self.assertRaises(ValueError):
            parse_program(page.replace("Manon Lescaut","Unknown work"),url=url)

if __name__=="__main__":
    unittest.main()
