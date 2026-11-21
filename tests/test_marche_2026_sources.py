"""Marche theatre-season evidence: public recite and one-ticket multiwork bills."""
import json
import unittest
from opera_atlas.marche_2026_parser import (
    JESI_URL,ANCONA_URL,PRODUCTIONS,read_program)
from scripts.discover_season_indexes import CONFIG,validate_config,extract,eligible
from scripts.collect_candidate_details import parse_source_credited_opera_detail

JESI_KEYS=["jesi-trittico-opera-2026","jesi-don-pasquale-opera-2026",
           "jesi-esecuzione-opera-2026","jesi-nabucco-opera-2026"]
ANCONA_KEYS=["ancona-elisir-opera-2026","ancona-cavalleria-program-2026"]

def jesi():
    return """
    <html><title>Programma Stagione Lirica 2026</title>
    <h1>59^ STAGIONE LIRICA DI TRADIZIONE</h1>
    <p>mercoledì 7 ottobre 2026, ore 16 – anteprima giovani*</p>
    <p>venerdì 9 ottobre 2026, ore 20.30</p>
    <p>domenica 11 ottobre 2026, ore 16**</p>
    <p>JESI, TEATRO PERGOLESI</p>
    <h2>IL TABARRO</h2><p>musica di Giacomo Puccini</p>
    <p>Personaggi e interpreti Michele Massimo Cavalletti</p>
    <h2>SUOR ANGELICA</h2><p>musica di Giacomo Puccini</p>
    <p>Personaggi e interpreti Suor Angelica Alessandra di Giorgio</p>
    <h2>GIANNI SCHICCHI</h2><p>musica di Giacomo Puccini</p>
    <p>direttore Stefano Vignati, regia Paul Emile Fourny</p>
    <p>mercoledì 28 ottobre 2026, ore 16 – anteprima giovani*</p>
    <p>venerdì 30 ottobre 2026, ore 20.30</p>
    <p>sabato 31 ottobre 2026, ore 20.30**</p>
    <p>JESI, TEATRO PERGOLESI</p><h2>DON PASQUALE</h2>
    <p>musica di Gaetano Donizetti</p><p>interpreti</p>
    <p>giovedì 12 novembre 2026, ore 16 – anteprima giovani*</p>
    <p>sabato 14 novembre 2026, ore 20.30</p>
    <p>domenica 15 novembre 2026, ore 16</p>
    <p>JESI, TEATRO PERGOLESI</p><h2>L'ESECUZIONE</h2>
    <p>Sotto lo sguardo di Tosca</p><p>musica di Salvatore Passantino</p>
    <p>interpreti</p>
    <p>giovedì 10 dicembre 2026, ore 16 – anteprima giovani*</p>
    <p>venerdì 11 dicembre 2026, ore 20.30</p>
    <p>domenica 13 dicembre 2026, ore 16**</p>
    <p>JESI, TEATRO PERGOLESI</p><h2>NABUCCO</h2>
    <p>musica di Giuseppe Verdi</p><p>interpreti, regia</p>
    <h2>QUERENCIA</h2><p>danza contemporanea</p>
    <h2>Progetti speciali</h2>
    <p>lunedì 20 aprile 2026, ore 10 (scuole)</p></html>
    """

def ancona():
    return """
    <html><title>stagione lirica 2026 – Fondazione Teatro delle Muse</title>
    <h1>ANCONA TEATRO DELLE MUSE "FRANCO CORELLI"</h1>
    <p>VENERDÌ 2 OTTOBRE ORE 20.30</p>
    <p>DOMENICA 4 OTTOBRE ORE 16.30</p>
    <p>mercoledì 30 settembre ore 18 anteprima giovani *</p>
    <h2>L’ELISIR D’AMORE</h2>
    <p>Melodramma giocoso – musica di Gaetano Donizetti</p>
    <p>GUIDA ALL’OPERA Ridotto Teatro delle Muse domenica 27 settembre ore 11</p>
    <p>VENERDÌ 4 DICEMBRE ORE 20.30</p>
    <p>DOMENICA 6 DICEMBRE ORE 16.30</p>
    <p>mercoledì 2 dicembre ore 18 anteprima giovani *</p>
    <h2>A GIACOMO LEOPARDI / CAVALLERIA RUSTICANA</h2>
    <p>musica di Pietro Mascagni</p>
    <h3>A GIACOMO LEOPARDI</h3><p>Poema musicale per orchestra e soprano</p>
    <h3>CAVALLERIA RUSTICANA</h3><p>Melodramma in un atto</p>
    <p>* spettacoli riservati agli studenti</p>
    </html>
    """

class MarcheOfficialSources(unittest.TestCase):
    def test_six_explicit_first_party_source_keys(self):
        doc=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources=validate_config(doc)
        self.assertEqual(len(sources),37)
        for key in JESI_KEYS+ANCONA_KEYS:
            self.assertIn(key,{x["key"] for x in sources})
            url=JESI_URL if key.startswith("jesi") else ANCONA_URL
            self.assertTrue(eligible(key,url))
            self.assertEqual(extract(key,url,jesi() if key.startswith("jesi") else ancona(),1),[url])

    def test_jesi_four_bills_exclude_all_youth_previews(self):
        expected=[
            [("2026-10-09","20:30"),("2026-10-11","16:00")],
            [("2026-10-30","20:30"),("2026-10-31","20:30")],
            [("2026-11-14","20:30"),("2026-11-15","16:00")],
            [("2026-12-11","20:30"),("2026-12-13","16:00")]
        ]
        for key,dates in zip(JESI_KEYS,expected):
            with self.subTest(key=key):
                title,composer,venue,recite,components=read_program(
                    jesi(),source_key=key,url=JESI_URL)
                self.assertEqual(venue,"Teatro Giovan Battista Pergolesi")
                self.assertEqual(recite,dates)
                self.assertEqual(composer,PRODUCTIONS[key][3])
                if key==JESI_KEYS[0]:
                    self.assertEqual(len(components),3)
                else:
                    facts=parse_source_credited_opera_detail(key,JESI_URL,jesi())
                    self.assertEqual(len(facts),2)

    def test_ancona_mixed_mascagni_bill_is_one_ticket_two_components(self):
        title,composer,venue,dates,parts=read_program(
            ancona(),source_key=ANCONA_KEYS[1],url=ANCONA_URL)
        self.assertEqual(venue,"Teatro delle Muse")
        self.assertEqual(dates,[("2026-12-04","20:30"),("2026-12-06","16:30")])
        self.assertEqual([v[0] for v in parts],
                         ["A Giacomo Leopardi","Cavalleria rusticana"])
        self.assertEqual(len(parse_source_credited_opera_detail(
            ANCONA_KEYS[0],ANCONA_URL,ancona())),2)

    def test_untrusted_sources_and_missing_or_conflicting_date_fail(self):
        for key,url,html in [(JESI_KEYS[3],JESI_URL,jesi()),
                             (ANCONA_KEYS[1],ANCONA_URL,ancona())]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    read_program(html,source_key=key,
                                 url=url.replace("www.","other."))
        with self.assertRaises(ValueError):
            read_program(jesi().replace("venerdì 11 dicembre 2026","venerdì 12 dicembre 2026"),
                         source_key=JESI_KEYS[3],url=JESI_URL)
        with self.assertRaises(ValueError):
            read_program(ancona().replace("musica di Pietro Mascagni",
                                          "musica di Antonio Vivaldi"),
                         source_key=ANCONA_KEYS[1],url=ANCONA_URL)

if __name__=="__main__":
    unittest.main()
