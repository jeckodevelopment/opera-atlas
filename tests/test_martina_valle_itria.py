"""Valle d'Itria first-party opera includes one opera in a ballet/opera bill."""
import json
import unittest
from datetime import date
from opera_atlas.martina_valle_itria import INDEX,extract_index,parse_detail
from opera_atlas.controlled_fetch import FetchResult
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import collect
from scripts.source_automation import INDEX_VENUES
from scripts.auto_catalogue import VENUE_BY_SOURCE,verified_venue
from scripts.rollover_season_indexes import ROLLOVER_KEYS,next_index
from scripts.publish_catalog_v2 import REGISTRY

KEY="martina-valle-itria-2026"
CARMEN="https://www.festivaldellavalleditria.it/spettacolo/carmen/2026-07-25"
DUET="https://www.festivaldellavalleditria.it/spettacolo/pulcinella-la-favola-di-orfeo/2026-07-14"
IL_SCHIAVO="https://www.festivaldellavalleditria.it/spettacolo/il-schiavo-di-sua-moglie/2026-07-24"
def page(title="Carmen",composer="Georges Bizet",venue="Palazzo Ducale",
         category="Opera",year=2026):
    facts=" ".join(f"{day} Luglio {year} . H 21:00 {venue}, Martina Franca"
                   for day in (25,28,31))
    return (f'<main><h1>{title}</h1><p>Musica di {composer}</p>'
            f'<p>Opéra-comique in quattro atti</p>'
            f'<p>{facts}</p><h2>Locandina</h2><p>Direttore Fabio Luisi</p>'
            f'<h4>Dettagli</h4><p>Quando: 25 Luglio {year}</p>'
            f'<p>Dove: {venue}, Martina Franca</p>'
            f'<p>Categoria: {category}</p></main>')
def doublebill():
    facts=" ".join(f"{d} Luglio 2026 . H 21:00 Palazzo Ducale, Martina Franca"
                   for d in (14,26,29))
    return ('<h1>Pulcinella / La favola di Orfeo (dittico)</h1>'
            '<p>Musiche di Igor Stravinskij e Alfredo Casella</p>'
            '<p>Pulcinella, balletto con canto in un atto.</p>'
            '<p>La favola di Orfeo: opera da camera in un atto.</p>'
            f'<p>{facts}</p><h2>Locandina</h2>'
            '<h4>Dettagli</h4><p>Dove: Palazzo Ducale, Martina Franca</p>'
            '<p>Categoria: Opera</p>')
class MartinaFestivalTests(unittest.TestCase):
    def test_approved_first_party_index_and_automatic_rollover(self):
        config=json.loads(CONFIG.read_text())
        source=next(x for x in validate_config(config) if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertEqual(INDEX_VENUES[KEY],
                         ("Martina Franca|Palazzo Ducale di Martina Franca",
                          "Martina Franca|Chiostro del Carmine"))
        self.assertEqual(VENUE_BY_SOURCE[KEY],
                         ("Martina Franca","Palazzo Ducale di Martina Franca"))
        self.assertIn(KEY,ROLLOVER_KEYS)
        self.assertIsNone(next_index(source,today=date(2026,8,31)))
        self.assertEqual(next_index(source,today=date(2026,9,1)),
                         INDEX.replace("2026","2027"))
        self.assertTrue(eligible(KEY,CARMEN))
        self.assertTrue(eligible(KEY,CARMEN.replace("2026","2028")))
        html=f'<a href="{CARMEN}">Carmen</a><a href="{DUET}">Dittico</a><a href="{IL_SCHIAVO}">Opera in altra sede</a>'
        self.assertEqual(extract(KEY,INDEX,html,2),[CARMEN,IL_SCHIAVO,DUET])
        with self.assertRaises(ValueError):extract_index("<p>Festival vuoto</p>",url=INDEX)

    def test_carmen_palace_only_and_canonical_evidence(self):
        self.assertEqual(parse_detail(page(),url=CARMEN),
                         ("Carmen","Georges Bizet",
                          "Palazzo Ducale di Martina Franca",
                          [("2026-07-25","21:00"),("2026-07-28","21:00"),
                           ("2026-07-31","21:00")]))
        candidate={"schema_version":1,"candidates":[{
            "id":"test-valle-itria-carmen","source_key":KEY,
            "official_url":CARMEN,"status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            self.assertEqual(url,CARMEN)
            return FetchResult(url,page(),"b"*64,100)
        result,health=collect(candidate,{"schema_version":1,"evidence":[]},
                             network_enabled=True,fetcher=fake,
                             today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        rows=result["evidence"][0]["event_facts"]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["starts_at"],"2026-07-25T21:00:00+02:00")
        registry=json.loads(REGISTRY.read_text())
        self.assertEqual(verified_venue(KEY,rows,registry)[:2],
                         ("Martina Franca","Palazzo Ducale di Martina Franca"))

    def test_mixed_ballet_opera_bill_promotes_only_casella(self):
        self.assertEqual(parse_detail(doublebill(),url=DUET),
                         ("La favola di Orfeo","Alfredo Casella",
                          "Palazzo Ducale di Martina Franca",
                          [("2026-07-14","21:00"),("2026-07-26","21:00"),
                           ("2026-07-29","21:00")]))
        self.assertNotIn("Pulcinella",parse_detail(doublebill(),url=DUET)[0])

    def test_mixed_orfeo_source_heading_markup_preserves_opera_only(self):
        # The official festival can collapse the slash spacing when H1
        # children are rendered into a single text string.
        html=doublebill().replace(
            "Pulcinella / La favola di Orfeo (dittico)",
            "Pulcinella/La favola di Orfeo (dittico)")
        title,composer,venue,recitals=parse_detail(html,url=DUET)
        self.assertEqual((title,composer,venue),
                         ("La favola di Orfeo","Alfredo Casella",
                          "Palazzo Ducale di Martina Franca"))
        self.assertEqual(len(recitals),3)
        for heading in ("Pulcinella / Altra opera (dittico)",
                        "Pulcinella / La favola di Orfeo (concerto)"):
            with self.subTest(heading=heading),self.assertRaises(ValueError):
                parse_detail(html.replace(
                    "Pulcinella/La favola di Orfeo (dittico)",heading),
                    url=DUET)

    def test_schiavo_verified_chiostro_is_not_attributed_to_palace(self):
        html=page(title="Il schiavo di sua moglie",
                  composer="Francesco Provenzale",
                  venue="Chiostro del Carmine")
        parsed=parse_detail(html,url=IL_SCHIAVO)
        self.assertEqual(parsed[:3],(
            "Il schiavo di sua moglie","Francesco Provenzale",
            "Chiostro del Carmine"))
        registry=json.loads(REGISTRY.read_text())
        facts=[{"venue":parsed[2],"date":day,
                "starts_at":day+"T21:00:00+02:00"}
               for day,_ in parsed[3]]
        self.assertEqual(verified_venue(KEY,facts,registry)[:2],
                         ("Martina Franca","Chiostro del Carmine"))
        mismatch=html.replace("Dove: Chiostro del Carmine",
                              "Dove: Palazzo Ducale")
        with self.assertRaisesRegex(ValueError,"mixed physical"):
            parse_detail(mismatch,url=IL_SCHIAVO)

    def test_concert_other_venue_and_partial_dates_are_excluded(self):
        for html in (
            page(category="Concerto"),
            page(venue="Teatro Comunale non verificato"),
            page(composer=""),
            page().replace("25 Luglio 2026 . H 21:00","25 Luglio 2027 . H 21:00"),
            page().replace("25 Luglio 2026 . H 21:00","32 Luglio 2026 . H 21:00"),
            doublebill().replace("Pulcinella, balletto","Pulcinella, opera"),
        ):
            with self.subTest(html=html[:130]),self.assertRaises(ValueError):
                parse_detail(html,url=DUET if "Pulcinella" in html else CARMEN)
        f=parse_detail(page(year=2028),
            url=CARMEN.replace("2026","2028"))
        self.assertEqual(f[3][0],("2028-07-25","21:00"))

if __name__=="__main__":
    unittest.main()
