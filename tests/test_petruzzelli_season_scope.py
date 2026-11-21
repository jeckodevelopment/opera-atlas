"""Source-scoped seasons must not revive old Petruzzelli opera URLs."""
import unittest
from scripts.discover_season_indexes import extract,reconcile_season_absences

SOURCE="petruzzelli-opera-2027"
INDEX="https://www.fondazionepetruzzelli.it/opera-e-balletto-2027/"
OFFICIAL=[
    "https://www.fondazionepetruzzelli.it/eventi/zenobia-di-niccolo-piccinni-27-29-gennaio/",
    "https://www.fondazionepetruzzelli.it/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/",
    "https://www.fondazionepetruzzelli.it/eventi/fidelio-di-ludwig-van-beethoven-19-25-novembre/",
]
OLD="https://www.fondazionepetruzzelli.it/eventi/la-notte-di-san-nicola-25-28-29-maggio/"

def page():
    return ("<nav><a href='"+OLD+"'>Archivio storico</a></nav>"
            "<h1>OPERA E BALLETTO 2027</h1>"
            +"".join("<a href='"+u+"'>Opera in stagione</a>" for u in OFFICIAL)
            +"<footer><a href='"+OLD+"'>Vedi anche vecchie stagioni</a></footer>")

class PetruzzelliOfficialSeasonScopeTests(unittest.TestCase):
    def test_2027_extracts_only_official_season_card_links(self):
        self.assertEqual(extract(SOURCE,INDEX,page(),min_links=3),sorted(OFFICIAL))

    def test_real_wordpress_div_heading_not_h1_or_h2(self):
        """The live season title may be a div, followed by h2 production cards."""
        html=("<nav><a href='/opera-e-balletto-2027/'>OPERA E BALLETTO 2027</a>"
              "<a href='"+OLD+"'>Archivio</a></nav>"
              "<div class='elementor-heading-title'>OPERA E BALLETTO 2027</div>"
              "<h2>Opere in programma</h2>"
              +"".join("<article><h2>Scheda</h2><a href='"+u+
                       "'>Opera</a></article>" for u in OFFICIAL)
              +"<footer><a href='"+OLD+"'>Archivio</a></footer>")
        self.assertEqual(extract(SOURCE,INDEX,html,min_links=3),sorted(OFFICIAL))
        with self.assertRaisesRegex(ValueError,"season index incomplete"):
            extract(SOURCE,INDEX,"<nav><a href='"+OFFICIAL[0]+
                    "'>OPERA E BALLETTO 2027</a></nav>",min_links=1)

    def test_old_candidate_keeps_audit_but_not_research_status(self):
        seen={
            "old":{"id":"old","source_key":SOURCE,"official_url":OLD,
                   "status":"needs_review"},
            "current":{"id":"current","source_key":SOURCE,
                       "official_url":OFFICIAL[0],"status":"needs_review"},
            "other":{"id":"other","source_key":"petruzzelli-opera-2026",
                     "official_url":OLD,"status":"needs_review"}}
        reconcile_season_absences(seen,SOURCE,OFFICIAL)
        self.assertEqual(seen["old"]["status"],"not_in_official_season")
        self.assertEqual(seen["current"]["status"],"needs_review")
        self.assertEqual(seen["other"]["status"],"needs_review")
        reconcile_season_absences(seen,SOURCE,[*OFFICIAL,OLD])
        self.assertEqual(seen["old"]["status"],"needs_review")

    def test_nonpetruzzelli_source_is_unchanged(self):
        seen={"old":{"id":"old","source_key":"scala-season-2026-27",
                     "official_url":OLD,"status":"needs_review"}}
        reconcile_season_absences(seen,"scala-season-2026-27",[])
        self.assertEqual(seen["old"]["status"],"needs_review")


if __name__=="__main__":
    unittest.main()
