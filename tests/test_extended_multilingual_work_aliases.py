"""Catalogued translations must map to existing permanent work IDs, never aliases as new works."""
import json
import unittest
from pathlib import Path
from opera_atlas.work_identity import ALIASES, canonical_title, resolve_work

REGISTRY=json.loads((Path(__file__).resolve().parents[1]/"data/identity-registry.json").read_text(encoding="utf-8"))

class ExpandedAliasCoverageTests(unittest.TestCase):
    def test_every_reviewed_translation_points_to_exactly_one_existing_work(self):
        ids={w["id"] for w in REGISTRY["works"].values()}
        self.assertGreaterEqual(len(ALIASES),30)
        for (alias,composer),title in ALIASES.items():
            with self.subTest(alias=alias,composer=composer):
                result=resolve_work(REGISTRY,alias,composer)
                self.assertIsNotNone(result)
                self.assertEqual(result["title"],title)
                self.assertIn(result["id"],ids)
                self.assertEqual(resolve_work(REGISTRY,title,composer)["id"],result["id"])

    def test_high_risk_homonymous_titles_are_not_conflated(self):
        for alias,composer in (
            ("The Barber of Seville","Giovanni Paisiello"),
            ("Cinderella","Jules Massenet"),
            ("Didone ed Enea","Giuseppe Verdi"),
            ("Don Chisciotte","Giovanni Paisiello"),
            ("The Bat","Giacomo Puccini"),
            ("Morte a Venezia","Thomas Mann"),
        ):
            with self.subTest(alias=alias,composer=composer):
                self.assertIsNone(resolve_work(REGISTRY,alias,composer))
                self.assertEqual(canonical_title(alias,composer),alias)

    def test_case_apostrophe_and_accent_variants_stay_safe(self):
        examples=(
            ("I PESCATORI DI PERLE","Georges Bizet","oa-w-000050"),
            ("THE TALES OF HOFFMANN","Jacques Offenbach","oa-w-000037"),
            ("Hansel and Gretel","Engelbert Humperdinck","oa-w-000057"),
            ("Don Chisciotte","Jules Massenet","oa-w-000030"),
            ("Ifigenia in Tauride","Christoph Willibald Gluck","oa-w-000061"),
            ("Didone ed Enea","Henry Purcell","oa-w-000052"),
            ("Die Fledermaus","Johann Strauss","oa-w-000028"),
            ("Morte a Venezia","Benjamin Britten","oa-w-000013"),
            ("Cinderella","Gioachino Rossini","oa-w-000068"),
            ("The Barber of Seville","Gioachino Rossini","oa-w-000038"),
            ("The Marriage of Figaro","Wolfgang Amadeus Mozart","oa-w-000045"),
            ("La carriera di un libertino","Igor' Stravinskij","oa-w-000053"),
            ("Il ritorno d'Ulisse in patria","Claudio Monteverdi","oa-w-000043"),
            ("Eugene Onegin","Pëtr Il'ič Čajkovskij","oa-w-000010"),
        )
        for alias,composer,work_id in examples:
            with self.subTest(alias=alias):
                self.assertEqual(resolve_work(REGISTRY,alias,composer)["id"],work_id)

    def test_alias_list_never_collides_with_a_different_canonical_record(self):
        # Fail if a new opera title is later introduced that an existing alias
        # would silently shadow or steal from a different permanent work.
        normalized=lambda x:x.casefold().replace("’","'").strip()
        for (alias,composer),canonical in ALIASES.items():
            matching=[w for w in REGISTRY["works"].values()
                      if normalized(w["title"])==normalized(alias)
                      and normalized(w["composer"])==normalized(composer)]
            self.assertFalse(any(w["title"]!=canonical for w in matching),
                             (alias,composer,canonical))

if __name__=="__main__":
    unittest.main()
