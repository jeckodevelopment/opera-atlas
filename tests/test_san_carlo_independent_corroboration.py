"""Independent showtime checks never imply primary-source authorization."""
import unittest

from scripts.corroborate_san_carlo_secondary import parse_independent, compare
from scripts.scan_san_carlo_secondary import build_secondary_checkpoint


def independent_fixture():
    return """<html><h1>Napoli - Teatro San Carlo</h1>
    <h2>Opera, Concerti &amp; Balletto - Stagione 2026/2027</h2>
    <h4>LUISA MILLER</h4><h5>Dicembre 2026</h5>
    <p>Dicembre: 02 (8h00 pm - Turno A), 03 (8h00 pm - F.A.), 06 (5h00 pm - Turno F)</p>
    <h5>DETTAGLI:</h5><p>Musica Giuseppe Verdi</p>
    <h4>OTTO MESI IN DUE ORE O SIA GLI ESILIATI IN SIBERIA</h4>
    <h5>Aprile 2027</h5><p>Aprile: 17 (8h00 pm - Turno A),
    21 (8h00 pm - Tagliando Opera B-F), 23 (8h00 pm - Turno C/D)</p>
    <h5>DETTAGLI:</h5><p>Musica Gaetano Donizetti</p>
    <h4>GALA ANNA RAZZI</h4><h5>Giugno 2027</h5>
    <p>Giugno: 03 (8h00 pm - Turno A)</p>
    </html>"""


def production(title, composer, dates):
    return {
        "title": title, "composer": composer,
        "venue": "Teatro di San Carlo", "city": "Napoli",
        "secondary_source": "https://www.classicalive.it/it/rassegne/teatro-di-san-carlo/stagione-dopera-2026-2027/",
        "review_status": "needs_primary_corroboration",
        "performances": [{"date": day, "time": clock} for day, clock in dates],
    }


class SanCarloIndependentReviewTests(unittest.TestCase):
    def candidate_doc(self):
        productions = [
            production("Luisa Miller", "Giuseppe Verdi", [
                ("2026-12-02", "20:00"), ("2026-12-03", "20:00"),
                ("2026-12-06", "17:00"),
            ]),
            production("Otto mesi in due ore o sia Gli esiliati in Siberia", "Gaetano Donizetti", [
                ("2027-04-17", "20:00"), ("2027-04-21", "18:00"),
                ("2027-04-23", "19:00"),
            ]),
        ]
        return build_secondary_checkpoint(productions, checked_at="now", incomplete=[])[0]

    def test_exact_independent_times_and_conflicts(self):
        observed = parse_independent(independent_fixture())
        self.assertEqual(observed["luisa miller"]["dates"]["2026-12-06"], "17:00")
        report = compare(self.candidate_doc(), observed)
        self.assertEqual(report["matching_recite_count"], 4)
        self.assertEqual(report["conflicting_recite_count"], 2)
        self.assertEqual(report["unmatched_recite_count"], 0)
        self.assertFalse(report["canonical_publication_authorized"])
        conflicts = next(x for x in report["productions"] if x["title"].startswith("Otto"))
        self.assertEqual({x["date"] for x in conflicts["conflicting_clocks"]},
                         {"2027-04-21", "2027-04-23"})
        self.assertEqual(conflicts["status"], "needs_date_review")

    def test_mixed_ballet_with_two_same_day_performances_is_outside_scope(self):
        html = independent_fixture().replace(
            '<h4>GALA ANNA RAZZI</h4>',
            '<h4>LA DAME AUX CAMÉLIAS</h4>'
        ).replace(
            '<p>Giugno: 03 (8h00 pm - Turno A)</p>',
            '<p>Giugno: 03 (5h00 pm - Turno A), 03 (9h00 pm - F.A.)</p>'
        )
        target = {"luisa miller", "otto mesi in due ore o sia gli esiliati in siberia"}
        observed = parse_independent(html, allowed_titles=target)
        self.assertEqual(set(observed), target)

    def test_no_secondary_calendar_is_not_success(self):
        with self.assertRaisesRegex(ValueError, "venue and season"):
            parse_independent("<h4>LUISA MILLER</h4><p>Dicembre: 02 (8h00 pm)</p>")
        with self.assertRaisesRegex(ValueError, "no dated events"):
            parse_independent("<h1>Napoli - Teatro San Carlo</h1>"
                              "<h2>Stagione 2026/2027</h2><h4>LUISA MILLER</h4>")

    def test_missing_second_source_is_not_fake_corroboration(self):
        report = compare(self.candidate_doc(), {
            "luisa miller": {"title": "LUISA MILLER", "dates": {"2026-12-02": "20:00"}}
        })
        self.assertEqual(report["matching_recite_count"], 1)
        self.assertEqual(report["unmatched_recite_count"], 5)
        self.assertFalse(report["canonical_publication_authorized"])

    def test_reject_tampered_candidate_provenance(self):
        doc = self.candidate_doc()
        doc["productions"][0]["corroboration_status"] = "approved"
        with self.assertRaisesRegex(ValueError, "provenance"):
            compare(doc, parse_independent(independent_fixture()))


if __name__ == "__main__":
    unittest.main()
