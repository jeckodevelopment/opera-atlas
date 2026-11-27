"""Regression checks for the November 27 Bellini and mixed-calendar audit."""
import unittest

from opera_atlas.catania_detail_parser import parse_detail
from scripts.discover_season_indexes import excluded_nonopera


def detail(title, rows):
    return (
        "<p>Luogo Teatro Massimo Bellini Via Giuseppe Perrotta</p>"
        "<p>Categoria Opere e Balletto</p><p>Data Mar 06 - 14 2027</p>"
        f"<h1>{title}</h1>"
        + "".join(f"<p>{row}</p>" for row in rows)
        + "<h3>Naviga sul sito</h3>"
    )


NABUCCO = [
    "Sabato 6 marzo 2027 ore 20.30 (Turno A)",
    "Domenica 7 marzo 2027 ore 17.30 (Turno R)",
    "Martedì 9 marzo 2027 ore 20.30 (Turno B)",
    "Mercoledì 10 marzo 2027 ore 17.30 (Turno S1)",
    "Venerdì 12 marzo 2027 ore 17.30 (Turno C)",
    "Sabato 13 marzo 2027 ore 17.30 (Turno S2)",
    "Domenica 14 marzo 2027 ore 17.30 (Turno D)",
]
RHEINGOLD = [
    "Venerdì 9 aprile 2027 ore 20.30 (Turno A)",
    "Sabato 10 aprile 2027 ore 17.30 (Turno R)",
    "Domenica 11 aprile 2027 ore 17.30 (Turno D)",
    "Martedì 13 aprile 2027 ore 17.30 (Turno S1)",
    "Mercoledì 14 aprile 2027 ore 20.30 (Turno B)",
    "Giovedì 15 aprile 2027 ore 17.30 (Turno S2)",
    "Venerdì 16 aprile 2027 ore 17.30 (Turno C)",
]
BASE = "https://www.teatromassimobellini.it/eventi/"


class PendingAuditTests(unittest.TestCase):
    def test_nabucco(self):
        title, composer, venue, rows = parse_detail(
            detail("Nabucco", NABUCCO), url=BASE + "nabucco/")
        self.assertEqual((title, composer, venue),
                         ("Nabucco", "Giuseppe Verdi", "Teatro Massimo Bellini"))
        self.assertEqual(rows, [
            ("2027-03-06", "20:30"), ("2027-03-07", "17:30"),
            ("2027-03-09", "20:30"), ("2027-03-10", "17:30"),
            ("2027-03-12", "17:30"), ("2027-03-13", "17:30"),
            ("2027-03-14", "17:30"),
        ])

    def test_rheingold(self):
        title, composer, _, rows = parse_detail(
            detail("Das Rheingold – L’oro del Reno", RHEINGOLD),
            url=BASE + "das-rheingold-loro-del-reno-2/")
        self.assertEqual((title, composer), ("Das Rheingold", "Richard Wagner"))
        self.assertEqual(rows, [
            ("2027-04-09", "20:30"), ("2027-04-10", "17:30"),
            ("2027-04-11", "17:30"), ("2027-04-13", "17:30"),
            ("2027-04-14", "20:30"), ("2027-04-15", "17:30"),
            ("2027-04-16", "17:30"),
        ])

    def test_incomplete_or_unknown_credit_not_promoted(self):
        with self.assertRaises(ValueError):
            parse_detail(detail("Nabucco", NABUCCO[:-1]), url=BASE + "nabucco/")
        with self.assertRaises(ValueError):
            parse_detail(detail("Nabucco", NABUCCO), url=BASE + "new-nabucco/")
        with self.assertRaises(ValueError):
            parse_detail(detail("Carmen", NABUCCO), url=BASE + "nabucco/")

    def test_source_scoped_exclusions(self):
        for slug in ("blu-planetaria", "interference", "madame-tour-estate-2026",
                     "la-cena", "bellini-alla-norma", "roberta-torre-masterclass"):
            self.assertTrue(excluded_nonopera(
                "taormina-arte-rolling-opera",
                "https://festivaltaorminarte.it/evento/" + slug + "/"))
        self.assertFalse(excluded_nonopera("bellini-catania-opera-2026-27",
                                          BASE + "nabucco/"))
        self.assertTrue(excluded_nonopera("bellini-catania-opera-2026-27",
                                         BASE + "concerto-di-capodanno-12/"))
        self.assertFalse(excluded_nonopera("taormina-arte-rolling-opera",
                                         "https://festivaltaorminarte.it/evento/norma/"))

    def test_trapani_peace_event_excluded_without_hiding_opera(self):
        base = "https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/"
        key = "trapani-luglio-musicale-2026"
        self.assertTrue(excluded_nonopera(key, base + "una-nota-per-la-pace/"))
        self.assertFalse(excluded_nonopera(key, base + "nabucco/"))
        self.assertFalse(excluded_nonopera("taormina-arte-rolling-opera",
                                          base + "una-nota-per-la-pace/"))
