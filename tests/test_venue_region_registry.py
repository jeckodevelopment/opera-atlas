"""All cities supported by source-approved venue resolution have known regions."""
import unittest
from scripts.auto_catalogue import VENUE_BY_SOURCE, ensure_venue


class VenueRegionRegistryTests(unittest.TestCase):
    def test_all_source_cities_can_be_provisioned(self):
        # Each official source must be able to introduce a new, independently
        # proven physical venue; no existing-venue cache is assumed.
        for key,(city,venue) in VENUE_BY_SOURCE.items():
            with self.subTest(source=key,city=city):
                registry={"venues":{}}
                record=ensure_venue(registry,city,venue,None)
                self.assertEqual(record["city"],city)
                self.assertTrue(record["region"])
                self.assertEqual(registry["venues"][city+"|"+venue],record)

    def test_known_distinct_regions_and_reject_unverified_city(self):
        expected={
            "Cosenza":"Calabria","Sabbioneta":"Lombardia",
            "Vicenza":"Veneto","Mantova":"Lombardia",
            "Trapani":"Sicilia","Milano":"Lombardia",
            "Ravenna":"Emilia-Romagna","Parma":"Emilia-Romagna",
            "Palermo":"Sicilia","Brescia":"Lombardia",
            "Genova":"Liguria",
        }
        for city,region in expected.items():
            with self.subTest(city=city):
                record=ensure_venue({"venues":{}},city,"Test Venue",None)
                self.assertEqual(record["region"],region)
        with self.assertRaisesRegex(ValueError,"Unknown City"):
            ensure_venue({"venues":{}},"Unknown City","Fake Theatre",None)

if __name__=="__main__":
    unittest.main()
