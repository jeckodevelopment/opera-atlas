"""Multilingual aliases resolve to exactly one canonical work, never an homonym."""
import json
import unittest
from pathlib import Path

from opera_atlas.work_identity import ALIASES, canonical_title, resolve_work
from scripts.collect_candidate_details import parse_known_opera_detail
from tests.test_sassari_de_carolis_source import page, URL

ROOT=Path(__file__).resolve().parents[1]

class CanonicalMultilingualIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((ROOT/"data/identity-registry.json").read_text(encoding="utf-8"))

    def test_four_language_pairs_and_permanent_ids(self):
        cases=[
            ("Don Carlo","Giuseppe Verdi","Don Carlos","oa-w-000071"),
            ("Nabucodonosor","Giuseppe Verdi","Nabucco","oa-w-000025"),
            ("Il flauto magico","Wolfgang Amadeus Mozart","Die Zauberflöte","oa-w-000056"),
            ("Tristano e Isotta","Richard Wagner","Tristan und Isolde","oa-w-000039"),
            ("Sansone e Dalila","Camille Saint-Saëns","Samson et Dalila","oa-w-000017"),
            ("Die Zauberflote","Wolfgang Amadeus Mozart","Die Zauberflöte","oa-w-000056"),
        ]
        for alias,composer,title,work_id in cases:
            with self.subTest(alias=alias):
                self.assertEqual(canonical_title(alias,composer),title)
                found=resolve_work(self.registry,alias,composer)
                self.assertIsNotNone(found)
                self.assertEqual((found["title"],found["id"]),(title,work_id))
                self.assertEqual(resolve_work(self.registry,title,composer)["id"],work_id)

    def test_never_conflate_composers_homonyms_or_unreviewed_titles(self):
        for title,composer in [
            ("Il flauto magico","Giuseppe Verdi"),
            ("Don Carlo","Gioachino Rossini"),
            ("Nabucodonosor","Gioachino Rossini"),
            ("Tristano e Isotta","Camille Saint-Saëns"),
            ("Sansone e Dalila","Richard Wagner"),
            ("Samson et Dalida","Camille Saint-Saëns"),
        ]:
            with self.subTest(title=title,composer=composer):
                self.assertIsNone(resolve_work(self.registry,title,composer))
        self.assertIsNone(resolve_work({"works":{
            "one":{"title":"Die Zauberflöte","composer":"Wolfgang Amadeus Mozart"},
            "two":{"title":"Die Zauberflöte","composer":"Wolfgang Amadeus Mozart"}
        }},"Il flauto magico","Wolfgang Amadeus Mozart"))

    def test_composer_metadata_resolves_without_changing_permanent_ids(self):
        examples = (
            ("Carmen", "Georges Bizet (1838–1875)", "oa-w-000009"),
            ("La Bohème", "Giacomo Puccini Opera", "oa-w-000024"),
            ("L’elisir d’amore", "Gaetano Donizetti Melodramma", "oa-w-000073"),
            ("Madama Butterfly", "Giacomo Puccini (1858–1924)", "oa-w-000019"),
            ("Norma", "Vincenzo Bellini Tragedia", "oa-w-000031"),
            ("Aida", "Giuseppe Verdi Opera", "oa-w-000015"),
            ("Il flauto magico", "Wolfgang Amadeus Mozart Opera", "oa-w-000056"),
        )
        for title, credit, expected in examples:
            with self.subTest(title=title, credit=credit):
                match = resolve_work(self.registry, title, credit)
                self.assertIsNotNone(match)
                self.assertEqual(match["id"], expected)

    def test_unverified_credit_suffix_or_wrong_composer_never_matches(self):
        examples = (
            ("La traviata", "Giuseppe Verdi Coro"),
            ("La traviata", "Giuseppe Verdi Opera di un altro autore"),
            ("La traviata", "Gioachino Rossini Opera"),
            ("Il barbiere di Siviglia", "Giovanni Paisiello Opera"),
            ("La Bohème", "Giacomo Puccini (1858-1924) Note"),
        )
        for title, credit in examples:
            with self.subTest(title=title, credit=credit):
                self.assertIsNone(resolve_work(self.registry, title, credit))

    def test_sassari_uses_shared_canonical_records_not_duplicate_works(self):
        for ident,expected in (("372","Die Zauberflöte"),("373","Don Carlos")):
            events=parse_known_opera_detail(
                "sassari-de-carolis-opera-2026",URL(ident),page(ident),self.registry)
            self.assertEqual(len(events),2)
            self.assertTrue(all(e["event_title"]==expected for e in events))
        self.assertFalse(any(w["title"] in ("Il flauto magico","Don Carlo")
                             for w in self.registry["works"].values()))

    def test_exact_alias_table_and_stable_composer_constraints(self):
        self.assertEqual(len(ALIASES),len(set(ALIASES)))
        for (title,composer),canonical in ALIASES.items():
            self.assertNotEqual(title,canonical.casefold())
            self.assertIsNotNone(resolve_work(self.registry,title,composer))
        for ambiguous in (""," ","Don Carlos"):
            with self.subTest(ambiguous=ambiguous):
                if not ambiguous.strip():
                    with self.assertRaises(ValueError):
                        canonical_title(ambiguous,"Giuseppe Verdi")
