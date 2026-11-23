"""Source-backed editorial profiles for two verified, still uncatalogued operas."""
import unittest
from scripts.auto_work_research import preverified_work_material,validated_editorial_attributions
from scripts.publish_catalog_v2 import slugify
from scripts.publish_work_editorial import validate_history

class TwoVerifiedEditorialProfiles(unittest.TestCase):
    def test_distinct_source_backed_productions_are_ready_for_identity_research(self):
        material=preverified_work_material()
        examples={
            "ghost-cafe":("Gabriela Fantato",2000,"Bergamo","Carlo Galante"),
            "il-schiavo-di-sua-moglie":(
                "Francesco Antonio Paolella",1672,"Napoli","Francesco Provenzale"),
        }
        for slug,(librettist,year,city,composer) in examples.items():
            with self.subTest(slug=slug):
                self.assertIn(slug,material)
                profile=material[slug]
                self.assertTrue(validate_history(profile["history"]))
                self.assertEqual(profile["history"]["librettist"],librettist)
                self.assertEqual(profile["history"]["premiere_year"],year)
                self.assertEqual(profile["history"]["premiere_city"],city)
                self.assertTrue(45<=len(profile["synopsis"])<=300)
                # The source's named composer stays mandatory for automatic
                # research. No fabricated Wikidata QID is introduced.
                attribution=validated_editorial_attributions().get(slug)
                self.assertIsNone(attribution)
        self.assertEqual(slugify("Il schiavo di sua moglie"),
                         "il-schiavo-di-sua-moglie")
