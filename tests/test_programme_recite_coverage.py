"""Coverage includes ticketed composite programmes without double-counting works."""
import unittest
from scripts.recite_coverage import detect

class ProgrammeReciteCoverageTests(unittest.TestCase):
    def test_brescia_dittico_is_published_once_per_date(self):
        published={"reviewed_on":"2026-11-23","productions":[]}
        programs={"programs":[{"venue":"Teatro Grande","municipality":"Brescia",
            "region":"Lombardia","components":[{"title":"Cavalleria rusticana"},
                                               {"title":"Pagliacci"}],
            "performances":[
                {"local_date":"2026-12-11","starts_at":"2026-12-11T20:00:00+01:00"},
                {"local_date":"2026-12-13","starts_at":"2026-12-13T15:30:00+01:00"}]}]}
        observations={"evidence":[{"event_facts":[
            {"venue":"Teatro Grande","date":"2026-12-11","starts_at":None},
            {"venue":"Teatro Grande","date":"2026-12-13","starts_at":None}]}]}
        row=detect(published,observations,programs)["venues"][0]
        self.assertEqual((row["published"],row["found"],row["missing"]),(2,2,0))

    def test_program_same_showtime_does_not_double_count_solo(self):
        published={"reviewed_on":"2026-11-23","productions":[{
            "venue":"Teatro Grande","municipality":"Brescia","region":"Lombardia",
            "dates":[["2026-12-11",None]]}]}
        programs={"programs":[{"venue":"Teatro Grande","municipality":"Brescia",
            "region":"Lombardia","performances":[
                {"local_date":"2026-12-11","starts_at":"2026-12-11T20:00:00+01:00"}]}]}
        row=detect(published,{"evidence":[]},programs)["venues"][0]
        self.assertEqual((row["published"],row["found"]),(1,1))

    def test_different_showtimes_remain_distinct(self):
        published={"reviewed_on":"2026-11-23","productions":[{
            "venue":"Teatro Grande","municipality":"Brescia","region":"Lombardia",
            "dates":[["2026-12-11","18:00"]]}]}
        programs={"programs":[{"venue":"Teatro Grande","municipality":"Brescia",
            "region":"Lombardia","performances":[
                {"local_date":"2026-12-11","starts_at":"2026-12-11T20:00:00+01:00"}]}]}
        row=detect(published,{"evidence":[]},programs)["venues"][0]
        self.assertEqual(row["published"],2)

if __name__=="__main__":
    unittest.main()
