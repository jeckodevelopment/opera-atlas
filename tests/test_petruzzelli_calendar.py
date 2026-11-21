"""Bari: Nabucco's seven official ticket dates are canonical and repeatable."""
import json
import unittest
from datetime import date

from opera_atlas.petruzzelli_detail_parser import parse_petruzzelli_detail
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.auto_catalogue import SOURCE_ALLOWLIST,promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract

SOURCE="petruzzelli-opera-2027"
INDEX="https://www.fondazionepetruzzelli.it/opera-e-balletto-2027/"
DETAIL="https://www.fondazionepetruzzelli.it/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/"
CID="oa-index-ef3fc228eb643db30288"
DATES=[("2027-03-12","20:30"),("2027-03-13","18:00"),
       ("2027-03-14","18:00"),("2027-03-16","20:30"),
       ("2027-03-17","20:30"),("2027-03-18","20:30"),
       ("2027-03-19","18:00")]

def page():
    times=[
        ("VENERDì",12,"20:30"),("SABATO",13,"18:00"),
        ("DOMENICA",14,"18:00"),("MARTEDì",16,"20:30"),
        ("MERCOLEDì",17,"20:30"),("GIOVEDì",18,"20:30"),
        ("VENERDì",19,"18:00")]
    return ('<h1>NABUCCO di Giuseppe Verdi | 12-19 MARZO</h1>'
            '<p>Giuseppe Verdi</p><p>Direttore Carlo Rizzi</p>'
            '<p>Orchestra e Coro del Teatro Petruzzelli</p>'
            '<p>giovedì 4 marzo 2027 | ore 19.00 '
            'ALBERTO MATTIOLI presenta l’opera Nabucco di Giuseppe Verdi</p>'
            '<h2>Orari Spettacoli</h2>'
            +''.join(f'<p>{day} {n} MARZO 2027 - {clock} | TURNO</p>'
                     for day,n,clock in times)
            +'<h3>Interpretato Da</h3><p>Nabucco IGOR GOLOVATENKO</p>')

class PetruzzelliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_index_only_approved_official_detail_pages(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(validate_config(config)),12)
        self.assertTrue(eligible(SOURCE,DETAIL))
        links=extract(SOURCE,INDEX,
            '<a href="/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/">Nabucco</a>'
            '<a href="/eventi/fidelio-di-beethoven/">Fidelio</a>'
            '<a href="/eventi/zenobia-piccinni/">Zenobia</a>'
            '<a href="/concertistica-2027/">Concerti</a>'
            '<a href="https://example.com/eventi/fake/">External</a>',3)
        self.assertEqual(len(links),3)
        self.assertFalse(eligible(SOURCE,INDEX))

    def test_seven_verified_nabucco_recite_and_no_conference(self):
        venue,dates=parse_petruzzelli_detail(
            page(),url=DETAIL,title="Nabucco",composer="Giuseppe Verdi")
        self.assertEqual(venue,"Teatro Petruzzelli")
        self.assertEqual(dates,DATES)
        rows=parse_known_opera_detail(SOURCE,DETAIL,page(),self.registry)
        self.assertEqual(len(rows),7)
        self.assertEqual({x["venue"] for x in rows},{"Teatro Petruzzelli"})
        self.assertEqual(rows[0]["starts_at"],"2027-03-12T20:30:00+01:00")
        self.assertEqual({x["composer"] for x in rows},{"Giuseppe Verdi"})

    def test_title_composer_month_weekday_and_origin_fail_closed(self):
        invalid=[
            page().replace("NABUCCO di Giuseppe Verdi","NABUCCO di Altro Compositore"),
            page().replace("VENERDì 12 MARZO","MARTEDì 12 MARZO"),
            page().replace("VENERDì 12 MARZO 2027","VENERDì 12 MARZO 2026"),
            page().replace("Orari Spettacoli","Data da confermare"),
            page().replace("SABATO 13 MARZO 2027 - 18:00",
                           "SABATO 13 MARZO 2027 - orario da definire"),
            page().replace("VENERDì 12 MARZO 2027 - 20:30",
                           "VENERDì 12 MARZO 2027 - 20:30 ANNULLATA"),
        ]
        for html in invalid:
            with self.subTest(html=html[-100:]):
                with self.assertRaises(ValueError):
                    parse_petruzzelli_detail(html,url=DETAIL,
                                             title="Nabucco",composer="Giuseppe Verdi")
        for bad in ("https://external.example/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/",
                    DETAIL+"?preview=1"):
            with self.assertRaises(ValueError):
                parse_petruzzelli_detail(page(),url=bad,
                                         title="Nabucco",composer="Giuseppe Verdi")

    def test_first_import_and_replay_keep_canonical_public_venue(self):
        rows=parse_known_opera_detail(SOURCE,DETAIL,page(),self.registry)
        candidates={"schema_version":1,"candidates":[
            {"id":CID,"source_key":SOURCE,"official_url":DETAIL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[
            {"candidate_id":CID,"source_key":SOURCE,"source_url":DETAIL,
             "status":"needs_editorial_review","event_facts":rows}]}
        approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        previously=any(p["source_url"]==DETAIL for p in self.facts["productions"])
        facts,ids,urls,report=promote(
            self.facts,self.registry,evidence,candidates,approved,
            today=date(2026,11,21))
        productions=[p for p in facts["productions"] if p["municipality"]=="Bari"]
        self.assertEqual(len(productions),1)
        self.assertEqual(productions[0]["title"],"Nabucco")
        self.assertEqual(productions[0]["dates"],[[d,t] for d,t in DATES])
        self.assertEqual(report["new_recite"],0 if previously else 7)
        self.assertEqual(report["new_stagings"],0 if previously else 1)
        self.assertIn("Bari|Teatro Petruzzelli",ids["venues"])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(
            sum(p["staging_id"]==ids["stagings"][productions[0]["key"]]["id"]
                for p in graph["performances"]),7)
        again,other_ids,other_urls,second=promote(
            facts,ids,evidence,candidates,urls,today=date(2026,11,21))
        self.assertEqual(second["new_recite"],0)
        self.assertEqual(again,facts)
        self.assertEqual(other_ids,ids)
        self.assertEqual(other_urls,urls)

if __name__=="__main__":
    unittest.main()
