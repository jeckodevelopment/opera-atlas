"""Ticket-partner source contracts using observed Rendano 2026 event text."""
import json
import unittest

from opera_atlas.cosenza_inprimafila_opera import (
    KEY,INDEX,eligible_detail,extract_index,parse_detail,
)
from scripts.discover_season_indexes import CONFIG,validate_config,extract,eligible
from scripts.collect_candidate_details import parse_source_credited_opera_detail

BARBIERE="https://www.inprimafila.net/index.php/eventi/barbiere-di-siviglia-cosenza"
NOZZE="https://www.inprimafila.net/index.php/eventi/le-nozze-di-figaro-cosenza"
MERE="https://www.inprimafila.net/index.php/eventi/la-mere-coupable-cosenza"

def fixture(title,when,credits,genre,venue="Teatro A.Rendano - Cosenza"):
    return (f"<html><h1>{title} - Cosenza</h1>"
            f"<div>{when}</div><p>{venue}</p>"
            f"<div>{title}</div><p>{credits}</p>"
            f"<p>{genre}</p><h3>Cast creativo</h3>"
            f"<p>regia Paolo Panizza</p><h3>Settori e Prezzi INTERI</h3></html>")

def rossini(when="Venerdi 13 Novembre Ore 20.30 - Domenica 15 Novembre 2026 Ore 17.00"):
    return fixture("BARBIERE DI SIVIGLIA",when,
                   "di GIOACHINO ROSSINI","opera buffa in 2 atti su libretto di Cesare Sterbini")

def mozart(when="Venerdi 11 Dicembre Ore 20.30 - Domenica 13 Dicembre 2026 Ore 17.00"):
    return fixture("LE NOZZE DI FIGARO",when,
                   "Ossia la folle giornata di WOLFGANG AMADEUS MOZART",
                   "opera buffa in 4 atti su libretto di Lorenzo Da Ponte")

def milhaud(when="Sabato 19 Dicembre 2026 Ore 20.30"):
    return fixture("LA MÈRE COUPABLE",when,"di DARIUS MILHAUD",
                   "atto unico su libretto di Madeleine Milhaud")

class CosenzaTicketFallback(unittest.TestCase):
    def test_exact_index_in_config_and_host_allowlist(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        row=next(x for x in validate_config(config) if x["key"]==KEY)
        self.assertEqual(row["url"],INDEX)
        for url in (BARBIERE,NOZZE,MERE):
            self.assertTrue(eligible_detail(url))
            self.assertTrue(eligible(KEY,url))
        for bad in (INDEX,NOZZE+"?print=1",MERE+"#hash",
                    "http://www.inprimafila.net/index.php/eventi/barbiere-di-siviglia-cosenza",
                    "https://evil.example/index.php/eventi/barbiere-di-siviglia-cosenza",
                    "https://www.inprimafila.net/index.php/news/barbiere-di-siviglia-cosenza"):
            self.assertFalse(eligible_detail(bad))

    def test_year_neutral_index_discovers_source_events(self):
        html=("<a href='/index.php/eventi/barbiere-di-siviglia-cosenza'>Barbiere</a>"
              "<a href='/index.php/eventi/le-nozze-di-figaro-cosenza'>Nozze</a>"
              "<a href='/index.php/eventi/la-mere-coupable-cosenza'>Mere</a>"
              "<a href='/index.php/eventi/schiaccianoci-cosenza'>Ballet</a>"
              "<a href='https://evil.example/index.php/eventi/barbiere-di-siviglia-cosenza'>bad</a>")
        self.assertEqual(extract_index(html),sorted([BARBIERE,NOZZE,MERE,
               "https://www.inprimafila.net/index.php/eventi/schiaccianoci-cosenza"]))
        self.assertEqual(extract(KEY,INDEX,html,1),extract_index(html))

    def test_exact_nonproduction_ticketing_links_are_not_candidates(self):
        from opera_atlas.cosenza_inprimafila_opera import INPRIMAFILA_NONPRODUCTION_SLUGS
        self.assertIn("stagione-l-altro-teatro-cosenza", INPRIMAFILA_NONPRODUCTION_SLUGS)
        self.assertIn("casa-delle-culture-cosenza", INPRIMAFILA_NONPRODUCTION_SLUGS)
        links=''.join('<a href="/index.php/eventi/'+slug+'">Altro</a>'
                       for slug in INPRIMAFILA_NONPRODUCTION_SLUGS)
        for slug in INPRIMAFILA_NONPRODUCTION_SLUGS:
            self.assertFalse(eligible_detail(
                "https://www.inprimafila.net/index.php/eventi/"+slug))
        self.assertEqual(extract_index(links+
            '<a href="/index.php/eventi/le-nozze-di-figaro-cosenza">Opera</a>'),
            [NOZZE])
        # Future operas beyond the current allowlist remain discoverable;
        # individual details are still required before publication.
        new="https://www.inprimafila.net/index.php/eventi/futura-opera-2030-cosenza"
        self.assertTrue(eligible_detail(new))

    def test_2026_public_operas_are_five_recitals_not_school_previews(self):
        rows=[]
        for url,html,title,composer,recitals in (
            (BARBIERE,rossini(),"Il barbiere di Siviglia","Gioachino Rossini",
             [("2026-11-13","20:30"),("2026-11-15","17:00")]),
            (NOZZE,mozart(),"Le nozze di Figaro","Wolfgang Amadeus Mozart",
             [("2026-12-11","20:30"),("2026-12-13","17:00")]),
            (MERE,milhaud(),"La mère coupable","Darius Milhaud",
             [("2026-12-19","20:30")]),
        ):
            with self.subTest(title=title):
                result=parse_detail(html,url=url)
                self.assertEqual(result,(title,composer,"Teatro Alfonso Rendano",recitals))
                facts=parse_source_credited_opera_detail(KEY,url,html)
                self.assertEqual(len(facts),len(recitals))
                rows.extend(facts)
        self.assertEqual(len(rows),5)
        self.assertTrue(all("10:00" not in str(r) for r in rows))

    def test_collect_routes_cosenza_through_strict_official_parser(self):
        from datetime import date
        from opera_atlas.controlled_fetch import FetchResult
        from scripts.collect_candidate_details import collect
        rows={"schema_version":1,"candidates":[{
            "id":"test-cosenza-mere","source_key":KEY,"official_url":MERE,
            "status":"needs_review"}]}
        def source_fetch(db,*,source_id,url,network_enabled):
            self.assertEqual(url,MERE)
            return FetchResult(url,milhaud(),"a"*64,100)
        evidence,health=collect(rows,{"schema_version":1,"evidence":[]},
                                network_enabled=True,fetcher=source_fetch,
                                today=date(2026,11,23))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        facts=evidence["evidence"][0]["event_facts"]
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]["event_title"],"La mère coupable")
        self.assertEqual(facts[0]["composer"],"Darius Milhaud")
        self.assertEqual(facts[0]["starts_at"],"2026-12-19T20:30:00+01:00")
        # The mixed source must never promote an unrelated play/ballet.
        with self.assertRaises(AssertionError):
            self.assertEqual(parse_source_credited_opera_detail(
                KEY,MERE,milhaud().replace("Teatro A.Rendano - Cosenza",
                                          "Altro teatro")),facts)

    def test_future_edition_does_not_depend_on_2026(self):
        html=mozart(when="Venerdi 11 Dicembre Ore 20.30 - Domenica 13 Dicembre 2027 Ore 17.00")
        self.assertEqual([day for day,_ in parse_detail(html,url=NOZZE)[3]],
                         ["2027-12-11","2027-12-13"])


    def test_real_structure_of_mixed_season_page_yields_five_operatic_recitals(self):
        from opera_atlas.cosenza_inprimafila_opera import parse_season_summary
        summary="https://www.inprimafila.net/index.php/eventi/stagione-lirica-2026-cosenza"
        html=(
            "<h1>STAGIONE LIRICA e BALLETTI 2026 - Cosenza</h1>"
            "<p>Sabato 31 Ottobre 2026 Ore 21.00</p><p>Teatro A.Rendano - Cosenza</p>"
            "<p>BARBIERE DI SIVIGLIA BALLET</p><p>Musica Gioachino Rossini</p>"
            "<p>Compagnia Artemis Danza</p>"
            "<p>Venerdi 13 Novembre Ore 20.30 - Domenica 15 Novembre 2026 Ore 17.00</p>"
            "<p>Teatro A.Rendano - Cosenza</p><p>BARBIERE DI SIVIGLIA</p>"
            "<p>Almaviva, o sia l'inutile precauzione</p>"
            "<p>di GIOACHINO ROSSINI</p><p>opera buffa in 2 atti su libretto di Cesare Sterbini</p>"
            "<p>Venerdi 11 Dicembre Ore 20.30 - Domenica 13 Dicembre 2026 Ore 17.00</p>"
            "<p>Teatro A.Rendano - Cosenza</p><p>LE NOZZE DI FIGARO</p>"
            "<p>Ossia la folle giornata di WOLFGANG</p><p>AMADEUS MOZART</p>"
            "<p>opera buffa in 4 atti su libretto di Lorenzo Da Ponte</p>"
            "<p>Sabato 19 Dicembre 2026 Ore 20.30</p>"
            "<p>Teatro A.Rendano - Cosenza</p>"
            "<p>LA MÈRE COUPABLE di DARIUS MILHAUD</p>"
            "<p>atto unico su libretto di Madeleine Milhaud</p>"
        )
        result=parse_season_summary(html,url=summary)
        self.assertEqual(len(result),3)
        self.assertEqual(sum(len(row[3]) for row in result),5)
        self.assertEqual({row[0] for row in result},
                         {"Il barbiere di Siviglia","Le nozze di Figaro","La mère coupable"})
        facts=parse_source_credited_opera_detail(KEY,summary,html)
        self.assertEqual(len(facts),5)
        self.assertEqual({f["composer"] for f in facts},
                         {"Gioachino Rossini","Wolfgang Amadeus Mozart","Darius Milhaud"})

    def test_season_dates_split_into_separate_joomla_text_nodes(self):
        from opera_atlas.cosenza_inprimafila_opera import parse_season_summary
        summary="https://www.inprimafila.net/index.php/eventi/stagione-lirica-2026-cosenza"
        html=(
            "<h1>STAGIONE LIRICA e BALLETTI 2026 - Cosenza</h1>"
            "<p>Sabato 31 Ottobre 2026</p><p>Ore 21.00</p>"
            "<p>Teatro A.Rendano - Cosenza</p><p>BARBIERE DI SIVIGLIA BALLET</p>"
            "<p>Compagnia Artemis Danza</p>"
            "<p>Venerdi 13 Novembre</p><p>Ore 20.30</p>"
            "<p>- Domenica 15 Novembre 2026</p><p>Ore 17.00</p>"
            "<p>Teatro A.Rendano - Cosenza</p><p>BARBIERE DI SIVIGLIA</p>"
            "<p>Almaviva, o sia l'inutile precauzione</p>"
            "<p>di GIOACHINO ROSSINI</p><p>opera buffa in 2 atti su libretto</p>"
            "<p>Venerdi 11 Dicembre</p><p>Ore 20.30</p>"
            "<p>- Domenica 13 Dicembre 2026</p><p>Ore 17.00</p>"
            "<p>Teatro A.Rendano - Cosenza</p><p>LE NOZZE DI FIGARO</p>"
            "<p>Ossia la folle giornata di WOLFGANG</p><p>AMADEUS MOZART</p>"
            "<p>opera buffa in 4 atti su libretto di Lorenzo Da Ponte</p>"
            "<p>Sabato 19 Dicembre 2026</p><p>Ore 20.30</p>"
            "<p>Teatro A.Rendano - Cosenza</p>"
            "<p>LA MÈRE COUPABLE di DARIUS MILHAUD</p>"
            "<p>atto unico su libretto di Madeleine Milhaud</p>"
        )
        result=parse_season_summary(html,url=summary)
        self.assertEqual({x[0]:len(x[3]) for x in result},{
            "Il barbiere di Siviglia":2,
            "Le nozze di Figaro":2,
            "La mère coupable":1,
        })

    def test_mixed_prose_and_missing_details_fail_closed(self):
        for url,html in (
            (BARBIERE,fixture("BARBIERE DI SIVIGLIA BALLET",
             "Sabato 31 Ottobre 2026 Ore 21.00","Gioachino Rossini","ballet")),
            (NOZZE,mozart().replace("Teatro A.Rendano - Cosenza","TAU - Cosenza")),
            (NOZZE,mozart().replace("opera buffa in 4 atti","commedia musicale")),
            (NOZZE,mozart().replace("WOLFGANG AMADEUS MOZART","Rossi")),
            (MERE,milhaud(when="Sabato 19 Dicembre Ore 20.30")),
            (MERE,milhaud(when="Sabato 39 Dicembre 2026 Ore 20.30")),
            (MERE,milhaud(when="Domenica 19 Dicembre 2026 Ore 10.00")
                .replace("LA MÈRE COUPABLE","LABORATORIO SCUOLE")),
        ):
            with self.subTest(url=url,html=html[:90]),self.assertRaises(ValueError):
                parse_detail(html,url=url)

if __name__=="__main__":
    unittest.main()
