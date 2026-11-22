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
        self.assertEqual(len(validate_config(config)),38)
        self.assertTrue(eligible(SOURCE,DETAIL))
        links=extract(SOURCE,INDEX,
            '<h1>OPERA E BALLETTO 2027</h1>'
            '<a href="/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/">Nabucco</a>'
            '<a href="/eventi/fidelio-di-beethoven/">Fidelio</a>'
            '<a href="/eventi/zenobia-piccinni/">Zenobia</a>'
            '<a href="/concertistica-2027/">Concerti</a>'
            '<a href="https://example.com/eventi/fake/">External</a>',3)
        self.assertEqual(len(links),3)
        self.assertFalse(eligible(SOURCE,INDEX))

    def test_2026_and_2027_indexes_stay_independently_monitored(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources={s["key"]:s for s in validate_config(config)}
        self.assertEqual(sources["petruzzelli-opera-2026"]["url"],
                         "https://www.fondazionepetruzzelli.it/opera-e-balletto-2026/")
        self.assertEqual(sources["petruzzelli-opera-2027"]["url"],INDEX)
        target="https://www.fondazionepetruzzelli.it/eventi/il-barbiere-di-siviglia-rossini-16-22-dicembre/"
        self.assertEqual(extract("petruzzelli-opera-2026",sources["petruzzelli-opera-2026"]["url"],
                                f'<h1>OPERA E BALLETTO 2026</h1><a href="{target}">Il barbiere di Siviglia</a>',1),[target])

    def test_barbiere_2026_has_six_exact_evening_and_matinee_times(self):
        url="https://www.fondazionepetruzzelli.it/eventi/il-barbiere-di-siviglia-rossini-16-22-dicembre/"
        html=('<h1>IL BARBIERE DI SIVIGLIA | ROSSINI | 16 - 22 DICEMBRE</h1>'
              '<p>Gioachino Rossini</p><p>Il barbiere di Siviglia di Gioachino Rossini</p>'
              '<p>direttore Stefano Montanari</p><h2>Orari Spettacoli</h2>'
              + "".join(f"<p>{day} {num} DICEMBRE 2026 - {time} | TURNO</p>"
                  for day,num,time in [("MERCOLEDì",16,"20:30"),("GIOVEDì",17,"20:30"),
                      ("VENERDì",18,"20:30"),("SABATO",19,"18:00"),
                      ("DOMENICA",20,"18:00"),("MARTEDì",22,"18:00")])
              + "<h3>Interpretato Da</h3>")
        with self.assertRaises(ValueError):
            parse_petruzzelli_detail(html,url=url,title="Il barbiere di Siviglia",composer="Gioachino Rossini")
        venue,dates=parse_petruzzelli_detail(html,url=url,title="Il barbiere di Siviglia",
                                             composer="Gioachino Rossini",season_year=2026)
        self.assertEqual(venue,"Teatro Petruzzelli")
        self.assertEqual(len(dates),6)
        self.assertEqual(dates[0],("2026-12-16","20:30"))
        self.assertEqual(dates[-1],("2026-12-22","18:00"))

    def test_other_opera_in_conversation_notice_cannot_steal_production_identity(self):
        # The official 2026 pages reuse a paragraph about La traviata;
        # that mention is not evidence the currently shown opera is Traviata.
        url="https://www.fondazionepetruzzelli.it/eventi/il-barbiere-di-siviglia-rossini-16-22-dicembre/"
        html=('<h1>IL BARBIERE DI SIVIGLIA | ROSSINI | 16 – 22 DICEMBRE</h1>'
              '<p>Gioachino Rossini</p>'
              '<p>Conversazione sull’opera La traviata di Giuseppe Verdi.</p>'
              '<h2>Orari Spettacoli</h2>'
              '<p>MERCOLEDì 16 DICEMBRE 2026 - 20:30 | TURNO A</p>'
              '<h3>Interpretato Da</h3>')
        rows=parse_known_opera_detail("petruzzelli-opera-2026",url,html,self.registry)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]["event_title"],rows[0]["composer"]),
                         ("Il barbiere di Siviglia","Gioachino Rossini"))
        with self.assertRaises(ValueError):
            parse_petruzzelli_detail(html,url=url,title="La traviata",
                                     composer="Giuseppe Verdi",season_year=2026)
        from opera_atlas.petruzzelli_detail_parser import verified_work_heading
        self.assertTrue(verified_work_heading(html,title="Il barbiere di Siviglia",
                                              composer="Gioachino Rossini"))
        self.assertFalse(verified_work_heading(html,title="La traviata",
                                               composer="Giuseppe Verdi"))

    def test_barbiere_2026_is_canonically_published_with_verified_poster(self):
        from scripts.publish_work_posters import OUTPUT as POSTERS
        url="https://www.fondazionepetruzzelli.it/eventi/il-barbiere-di-siviglia-rossini-16-22-dicembre/"
        matches=[p for p in self.facts["productions"] if p["source_url"]==url]
        self.assertEqual(len(matches),1)
        production=matches[0]
        self.assertEqual((production["title"],production["composer"]),
                         ("Il barbiere di Siviglia","Gioachino Rossini"))
        self.assertEqual(production["dates"],[
            ["2026-12-16","20:30"],["2026-12-17","20:30"],
            ["2026-12-18","20:30"],["2026-12-19","18:00"],
            ["2026-12-20","18:00"],["2026-12-22","18:00"]])
        identity=self.registry["works"]["il barbiere di siviglia|gioachino rossini"]
        self.assertEqual(identity["id"],"oa-w-000038")
        staging=self.registry["stagings"][production["key"]]
        self.assertEqual(staging["work_id"],identity["id"])
        self.assertEqual(staging["venue_id"],self.registry["venues"]["Bari|Teatro Petruzzelli"]["id"])
        catalog=assemble(self.facts,self.registry)
        self.assertEqual(sum(x["staging_id"]==staging["id"]
                             for x in catalog["performances"]),6)
        posters=json.loads(POSTERS.read_text(encoding="utf-8"))["works"]
        # The archival illustration can be upgraded when the source-linked
        # publisher verifies authentic official production art. Both are
        # acceptable with their respective provenance checks.
        self.assertIn(posters[identity["id"]]["kind"],
                      {"archival_work_image","official_production_image"})
        from scripts.publish_work_posters import check as validate_posters
        validate_posters()

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
        productions=[p for p in facts["productions"] if p["municipality"]=="Bari" and p["source_url"]==DETAIL]
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
