"""Deterministic publication-safe synopsis extraction tests."""
import unittest

from scripts.work_plot_generator import synopsis_from_wikipedia_plot


class PlotGeneratorTests(unittest.TestCase):
    def test_two_related_facts_create_original_short_synopsis(self):
        page = ("Anna Bolena è un'opera in due atti. "
                "== Trama == "
                "Anna si innamora di Enrico. "
                "In seguito Enrico cerca di liberare Anna dalla prigionia. "
                "La corte osserva le vicende e le conseguenze. "
                "== Note == Archivio di riferimento.")
        synopsis = synopsis_from_wikipedia_plot(page)
        self.assertEqual(
            synopsis,
            "Nella vicenda, Anna prova amore per Enrico; Enrico tenta di liberare Anna.")
        self.assertTrue(45 <= len(synopsis) <= 220)
        self.assertNotIn(synopsis, page)

    def test_plaintext_wikipedia_section_heading(self):
        page = ("Opera e personaggi.\nTrama\n"
                "Anna ama Enrico. Enrico accusa Anna di tradimento. "
                "Gli altri personaggi affrontano le conseguenze.\n"
                "Bibliografia\nEnrico uccide Giulio.")
        result = synopsis_from_wikipedia_plot(page)
        self.assertIn("Anna prova amore per Enrico", result)
        self.assertIn("Enrico accusa Anna", result)
        self.assertNotIn("Giulio", result)

    def test_insufficient_plot_is_not_rewritten_or_invented(self):
        self.assertIsNone(synopsis_from_wikipedia_plot(
            "Anna si innamora di Enrico. Enrico cerca di liberare Anna."))
        self.assertIsNone(synopsis_from_wikipedia_plot(
            "== Trama == Anna si innamora di Enrico."))
        self.assertIsNone(synopsis_from_wikipedia_plot(
            "== Trama == Nessuna descrizione narrativa specifica. " * 10))

    def test_unrelated_characters_do_not_get_fused(self):
        article = ("== Trama == " + "La vicenda si sviluppa a corte. " * 5
                   + "Anna si innamora di Enrico. "
                   + "Giulio cerca di liberare Maria.")
        self.assertIsNone(synopsis_from_wikipedia_plot(article))

    def test_extra_sections_are_not_used_as_plot(self):
        page = ("== Trama == Nessun dettaglio sulla vicenda. "
                "== Note == " + "Anna si innamora di Enrico. "
                "Enrico cerca di liberare Anna. " * 8)
        self.assertIsNone(synopsis_from_wikipedia_plot(page))


if __name__ == "__main__":
    unittest.main()
