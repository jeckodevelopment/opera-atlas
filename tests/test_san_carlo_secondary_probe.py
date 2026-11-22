"""Isolated secondary San Carlo calendar: focused parsing without publication."""
import unittest

from scripts.scan_san_carlo_secondary import URL, parse, build_secondary_checkpoint


def fixture():
    return """
    <html><h1>Teatro di San Carlo</h1><p>Napoli</p>
    <p>Giuseppe Verdi</p><h2>Luisa Miller</h2>
    <div><span>Teatro di San Carlo</span><span>Napoli</span></div>
    <h3>Recite</h3>
    <a href="/it/eventi/2026-12-02/luisa-miller/">Mer 2 Dicembre 2026 20:00</a>
    <a href="/it/eventi/2026-12-03/luisa-miller/">Gio 3 Dicembre 2026 20:00</a>
    <a href="https://www.teatrosancarlo.it/spettacoli/luisa-miller/">BIGLIETTI</a>
    <h3>Personaggi e interpreti</h3>
    <a href="/cast">2 Dic, 3 Dic</a><p>Maria Rossi</p>
    <p>Giacomo Puccini</p><h2>Madama Butterfly</h2>
    <p>Teatro di San Carlo</p><h3>Recite</h3>
    <a href="/it/eventi/2027-01-17/madama-butterfly/">Dom 17 Gennaio 2027 17:00</a>
    <a href="https://www.teatrosancarlo.it/spettacoli/madama-butterfly/">BIGLIETTI</a>
    <h2>Altre edizioni Teatro di San Carlo</h2></html>
    """


class SecondarySanCarloTests(unittest.TestCase):
    def test_exact_titles_composers_performance_clocks(self):
        productions = parse(fixture())
        self.assertEqual(len(productions), 2)
        self.assertEqual(productions[0]["title"], "Luisa Miller")
        self.assertEqual(productions[0]["composer"], "Giuseppe Verdi")
        self.assertEqual(productions[0]["official_event_url"], "https://www.teatrosancarlo.it/spettacoli/luisa-miller/")
        self.assertEqual(productions[1]["composer"], "Giacomo Puccini")
        self.assertEqual(productions[0]["performances"], [
            {"date": "2026-12-02", "time": "20:00"},
            {"date": "2026-12-03", "time": "20:00"},
        ])
        self.assertEqual(productions[1]["performances"], [
            {"date": "2027-01-17", "time": "17:00"}])
        self.assertTrue(all(p["review_status"] == "needs_primary_corroboration"
                            for p in productions))

    def test_ignores_images_cast_and_unrelated_layout(self):
        noisy = fixture().replace(
            "<p>Teatro di San Carlo</p><h3>Recite</h3>",
            "<img src='/unimportant.jpg'><p>Teatro di San Carlo</p><h3>Recite</h3>")
        self.assertEqual(parse(noisy), parse(fixture()))

    def test_incomplete_nonproduction_heading_is_reported_not_fatal(self):
        noisy = fixture().replace(
            '<h2>Altre edizioni Teatro di San Carlo</h2>',
            '<p>Vincenzo Bellini</p><h2>Altre edizioni Teatro di San Carlo</h2>'
        )
        skipped = []
        productions = parse(noisy, diagnostics=skipped)
        self.assertEqual(len(productions), 2)
        self.assertTrue(all("recite" in item["missing"] for item in skipped))
        self.assertTrue(all(item["heading"] != productions[0]["title"] for item in skipped))

    def test_realistic_heading_and_plaintext_recite_markup(self):
        realistic = fixture().replace("<h3>Recite</h3>", "<h4>Recite</h4>")
        realistic = realistic.replace(
            '<a href="/it/eventi/2026-12-02/luisa-miller/">Mer 2 Dicembre 2026 20:00</a>',
            '<div>Mer 2 Dicembre 2026 20:00</div>'
        )
        productions = parse(realistic)
        self.assertEqual(len(productions), 2)
        self.assertEqual(len(productions[0]["performances"]), 2)

    def test_nested_heading_inside_outer_anchor(self):
        html = fixture().replace(
            '<p>Giuseppe Verdi</p><h2>Luisa Miller</h2>',
            '<a href="/produzione/luisa-miller"><p>Giuseppe Verdi</p>'
            '<h2><span>Luisa Miller</span></h2></a>',
        )
        records = parse(html)
        self.assertEqual(records[0]["title"], "Luisa Miller")
        self.assertEqual(records[0]["composer"], "Giuseppe Verdi")
        self.assertEqual(len(records[0]["performances"]), 2)

    def test_checkpoint_is_unverified_and_deterministic(self):
        rows = parse(fixture())
        doc, health = build_secondary_checkpoint(
            rows, checked_at="2026-11-22T21:54:44Z",
            incomplete=[{"heading": "Iscriviti alla newsletter", "missing": ["recite"]}]
        )
        self.assertEqual(doc["source_role"], "secondary_unverified")
        self.assertEqual(len(doc["productions"]), 2)
        self.assertTrue(all(
            x["corroboration_status"] == "pending_independent_event_verification"
            for x in doc["productions"]))
        self.assertFalse(health["published"])
        self.assertEqual(health["performance_count"], 3)
        self.assertNotIn("event_facts", str(doc))
        # Refreshing the same page does not change the canonical input.
        self.assertEqual(doc, build_secondary_checkpoint(
            rows, checked_at="2026-11-23T21:54:44Z", incomplete=[])[0])

    def test_checkpoint_refuses_untrusted_or_ambiguous_clocks(self):
        rows = parse(fixture())
        rows[0]["performances"].append({"date": "2026-12-02", "time": "20:00"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_secondary_checkpoint(rows, checked_at="now", incomplete=[])
        rows = parse(fixture())
        rows[0]["review_status"] = "approved"
        with self.assertRaisesRegex(ValueError, "untrusted"):
            build_secondary_checkpoint(rows, checked_at="now", incomplete=[])

    def test_official_ticket_reference_is_mandatory_for_a_candidate(self):
        html = fixture().replace(
            '<a href="https://www.teatrosancarlo.it/spettacoli/luisa-miller/">BIGLIETTI</a>',
            '<a href="https://evil.example/spettacoli/luisa-miller/">BIGLIETTI</a>'
        )
        skipped = []
        result = parse(html, diagnostics=skipped)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Madama Butterfly")
        self.assertTrue(any("official_ticket" in row["missing"] for row in skipped))

    def test_rejects_wrong_source_and_ambiguous_time(self):
        with self.assertRaisesRegex(ValueError, "unapproved"):
            parse(fixture(), url="https://not-classicalive.example/season")
        with self.assertRaisesRegex(ValueError, "weekday/date mismatch"):
            parse(fixture().replace("Mer 2 Dicembre", "Dom 2 Dicembre"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse(fixture().replace(
                '<h3>Personaggi e interpreti</h3>',
                '<a href="/duplicate">Gio 3 Dicembre 2026 20:00</a><h3>Personaggi e interpreti</h3>'))

    def test_does_not_accept_empty_season_or_wrong_venue(self):
        with self.assertRaises(ValueError):
            parse("<h1>Teatro di San Carlo</h1><p>Napoli</p>")
        with self.assertRaises(ValueError):
            parse(fixture().replace("<h1>Teatro di San Carlo</h1>", "<h1>Altro</h1>")
                  .replace("<span>Teatro di San Carlo</span>", "<span>Teatro Altro</span>")
                  .replace("<p>Teatro di San Carlo</p>", "<p>Teatro Altro</p>")
                  .replace("Teatro di San Carlo</h2>", "Teatro Altro</h2>"))


if __name__ == "__main__":
    unittest.main()
