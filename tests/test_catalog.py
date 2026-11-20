"""Curated repertoire identity, aliases and explicit opera classification."""
import unittest

from opera_atlas.catalog import (
    AmbiguousWorkError, find_work, register_alias, register_work,
)
from opera_atlas.db import connect, migrate


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_verified_alias_matches_only_correct_composer(self):
        verdi = register_work(self.db, "La traviata", "Giuseppe Verdi")
        register_alias(self.db, verdi, "Traviata")
        self.assertEqual(find_work(self.db, " traviata ", composer="GIUSEPPE VERDI"), verdi)
        self.assertIsNone(find_work(self.db, "Traviata", composer="Another composer"))

    def test_missing_composer_not_auto_linked(self):
        register_work(self.db, "Rigoletto", "Giuseppe Verdi")
        self.assertIsNone(find_work(self.db, "Rigoletto", composer=None))
        self.assertIsNone(find_work(self.db, "Rigoletto", composer=" "))

    def test_homonymous_verified_work_requires_review(self):
        register_work(self.db, "Example", "Test Composer")
        register_work(self.db, "Example", "Test Composer")
        with self.assertRaises(AmbiguousWorkError):
            find_work(self.db, "Example", composer="Test Composer")

    def test_genre_filter_prevents_concert_masquerading_as_opera(self):
        concert = register_work(self.db, "Verdi Gala", "Giuseppe Verdi", genre="concert")
        self.assertEqual(find_work(self.db, "Verdi Gala", composer="Giuseppe Verdi", genre="concert"), concert)
        self.assertIsNone(find_work(self.db, "Verdi Gala", composer="Giuseppe Verdi", genre="opera"))

    def test_invalid_genre_rejected(self):
        with self.assertRaises(ValueError):
            register_work(self.db, "Opera", "Composer", genre="fictional")

    def test_empty_alias_rejected(self):
        work = register_work(self.db, "Tosca", "Giacomo Puccini")
        with self.assertRaises(ValueError):
            register_alias(self.db, work, "   ")

    def test_unknown_work_alias_rejected(self):
        with self.assertRaises(ValueError):
            register_alias(self.db, 999, "Alias")

    def test_repeated_alias_idempotent(self):
        work = register_work(self.db, "Carmen", "Georges Bizet")
        register_alias(self.db, work, "La Carmen")
        register_alias(self.db, work, "  LA   CARMEN ")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM work_aliases").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
