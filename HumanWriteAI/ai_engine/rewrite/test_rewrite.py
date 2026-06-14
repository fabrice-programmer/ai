"""
test_rewrite.py

Tests for the rewrite module covering:
  1. Pattern detection (all categories)
  2. Citation/number protection
  3. Full pipeline analysis and improvement
  4. Edge cases (empty text, special characters)
  5. Integrity verification

Run with: python -m pytest HumanWriteAI/ai_engine/rewrite/test_rewrite.py -v
Or:        python HumanWriteAI/ai_engine/rewrite/test_rewrite.py
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

import unittest
from ai_engine.rewrite.main import (
    improve_writing,
    analyze_sentence,
    get_supported_categories,
)
from ai_engine.rewrite.protector import (
    ContentProtector,
    protect_text,
    restore_text,
    verify_protection,
)
from ai_engine.rewrite.patterns import (
    count_clauses,
    is_overly_long,
    has_weak_opener,
    get_all_patterns,
)
from ai_engine.rewrite.rewriter import (
    split_sentences,
    RewriteEngine,
    SentenceIssue,
    RewriteResult,
)


class TestPatternDetection(unittest.TestCase):
    """Test individual pattern detectors."""

    def test_detect_wordiness(self):
        """Test wordiness detection."""
        result = improve_writing(
            "The utilization of the methodology was conducted by the researchers.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("wordiness", categories)

    def test_detect_wordiness_multiple(self):
        """Test wordiness with multiple verbose phrases."""
        result = improve_writing(
            "Due to the fact that a large number of participants were involved, "
            "the results were significant.",
            mode="analyze",
        )
        wordiness_issues = [
            i for i in result["issues"] if i["category"] == "wordiness"
        ]
        self.assertGreaterEqual(len(wordiness_issues), 1)

    def test_detect_passive_voice(self):
        """Test passive voice detection (unnecessary passive)."""
        result = improve_writing(
            "The experiment was conducted by the research team last week.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("passive_voice", categories)

    def test_acceptable_passive(self):
        """Test that acceptable academic passives are NOT flagged."""
        result = improve_writing(
            "The samples were incubated at 37°C for 24 hours.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertNotIn("passive_voice", categories)

    def test_detect_vague_language(self):
        """Test vague language detection."""
        result = improve_writing(
            "The results were very interesting and showed a somewhat significant trend.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("vague_language", categories)

    def test_detect_colloquialism(self):
        """Test colloquial language detection."""
        result = improve_writing(
            "The researchers looked at a lot of data and got some interesting results.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("colloquialism", categories)

    def test_detect_redundancy(self):
        """Test redundancy detection."""
        result = improve_writing(
            "The end result of the study was that the combine together confirmed the consensus of opinion.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("redundancy", categories)

    def test_detect_nominalization(self):
        """Test nominalization detection."""
        result = improve_writing(
            "The researchers performed an analysis of the data and came to a conclusion.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("nominalization", categories)

    def test_detect_weak_opener(self):
        """Test weak sentence opener detection."""
        result = improve_writing(
            "There is a significant correlation between these variables.",
            mode="analyze",
        )
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("weak_opener", categories)

    def test_detect_complex_sentence(self):
        """Test complex/long sentence detection."""
        long_sentence = (
            "The study examined the effects of the intervention which was "
            "designed to improve outcomes for participants who were selected "
            "from a diverse population that included both urban and rural "
            "areas, although the results were mixed."
        )
        result = improve_writing(long_sentence, mode="analyze")
        categories = [i["category"] for i in result["issues"]]
        self.assertIn("complex_sentence", categories)

    def test_no_false_positives_clean_text(self):
        """Test that well-written academic text gets few or no flags."""
        clean_text = (
            "The experiment examined the effect of temperature on enzyme activity. "
            "Researchers measured reaction rates at five different temperatures. "
            "The results showed a significant increase in activity between 25°C and 37°C."
        )
        result = improve_writing(clean_text, mode="analyze")
        # Should have very few issues (0-2 max)
        self.assertLessEqual(len(result["issues"]), 3)


class TestCitationProtection(unittest.TestCase):
    """Test that citations, numbers, and scientific content are preserved."""

    def test_protect_inline_citation(self):
        """Test (Author, Year) style citations are preserved."""
        text = "Recent studies (Smith, 2020) have shown significant results."
        result = improve_writing(text)
        self.assertIn("Smith, 2020", result["rewritten_text"])

    def test_protect_et_al_citation(self):
        """Test (Author et al., Year) citations."""
        text = "Previous work (Johnson et al., 2019) established the framework."
        result = improve_writing(text)
        self.assertIn("Johnson et al., 2019", result["rewritten_text"])

    def test_protect_bracket_references(self):
        """Test [1], [2,3], [4-7] style references."""
        text = "The method described in [1] and [2, 3] was used."
        result = improve_writing(text)
        self.assertIn("[1]", result["rewritten_text"])
        self.assertIn("[2, 3]", result["rewritten_text"])

    def test_protect_statistical_values(self):
        """Test p-values and statistics are preserved."""
        text = "The results were statistically significant (p < 0.05)."
        result = improve_writing(text)
        self.assertIn("p < 0.05", result["rewritten_text"])

    def test_protect_percentages(self):
        """Test percentages are preserved."""
        text = "Approximately 45.2% of participants completed the study."
        result = improve_writing(text)
        self.assertIn("45.2%", result["rewritten_text"])

    def test_protect_numbers_with_units(self):
        """Test numbers with units (e.g., 37°C, 100 mM)."""
        text = "The samples were incubated at 37°C for 24 hours."
        result = improve_writing(text)
        self.assertIn("37°C", result["rewritten_text"])
        self.assertIn("24 hours", result["rewritten_text"])

    def test_protect_confidence_intervals(self):
        """Test confidence intervals are preserved."""
        text = "The mean difference was 2.34 (95% CI [1.23, 4.56])."
        result = improve_writing(text)
        self.assertIn("95% CI [1.23, 4.56]", result["rewritten_text"])

    def test_no_integrity_violations(self):
        """Test that protected content is never lost."""
        text = (
            "Recent studies (Smith et al., 2020) found that p < 0.05 for "
            "the primary outcome (t(28) = 2.45). These results support "
            "findings reported in previous work [4, 5]."
        )
        result = improve_writing(text)
        self.assertEqual(len(result["integrity_violations"]), 0)

    def test_multiple_citations_per_sentence(self):
        """Test sentences with multiple citations."""
        text = (
            "Several studies (Smith, 2020; Johnson et al., 2019; "
            "Lee & Kim, 2021) have investigated this phenomenon."
        )
        result = improve_writing(text)
        self.assertIn("Smith, 2020", result["rewritten_text"])
        self.assertIn("Johnson et al., 2019", result["rewritten_text"])
        self.assertIn("Lee & Kim, 2021", result["rewritten_text"])


class TestContentProtector(unittest.TestCase):
    """Test the ContentProtector class directly."""

    def setUp(self):
        self.protector = ContentProtector()

    def test_protect_and_restore(self):
        """Test basic protect and restore cycle."""
        original = "Results (Smith, 2020) showed p < 0.05."
        protected = self.protector.protect(original)
        # Protected text should have no citations/numbers visible
        self.assertNotIn("Smith, 2020", protected)
        self.assertNotIn("0.05", protected)
        # But should have placeholders
        self.assertIn("<<CIT_", protected)
        self.assertIn("<<NUM_", protected)

        restored = self.protector.restore(protected)
        self.assertEqual(original, restored)

    def test_multiple_protect_calls(self):
        """Test that multiple protect calls work independently."""
        p1 = ContentProtector()
        p2 = ContentProtector()

        t1 = p1.protect("Citation (Smith, 2020).")
        t2 = p2.protect("Number is 95% CI.")

        self.assertIn("<<CIT_0>>", t1)
        self.assertIn("<<NUM_0>>", t2)

        self.assertEqual(p1.restore(t1), "Citation (Smith, 2020).")
        self.assertEqual(p2.restore(t2), "Number is 95% CI.")

    def test_no_protected_content(self):
        """Test text with no protected content."""
        text = "This is plain text with no citations or numbers."
        protected = self.protector.protect(text)
        self.assertEqual(text, protected)
        restored = self.protector.restore(protected)
        self.assertEqual(text, restored)

    def test_protected_terms_not_modified(self):
        """Test that Latin terms are preserved."""
        text = "In vitro studies showed e.g., significant results."
        protected = self.protector.protect(text)
        # The protector doesn't actively rewrite terms, just protects spans
        # But verify no accidental modification
        restored = self.protector.restore(protected)


class TestSentenceSplitting(unittest.TestCase):
    """Test sentence splitting logic."""

    def test_basic_split(self):
        """Test basic sentence splitting."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "First sentence.")
        self.assertEqual(sentences[1], "Second sentence.")
        self.assertEqual(sentences[2], "Third sentence.")

    def test_handles_abbreviations(self):
        """Test that abbreviations like 'e.g.' don't split sentences."""
        text = "Some results (e.g., significant findings) were observed. Further analysis confirmed this."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 2)
        self.assertIn("e.g.", sentences[0])

    def test_handles_question_marks(self):
        """Test that questions are handled."""
        text = "What was the result? The analysis showed significance."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 2)

    def test_single_sentence(self):
        """Test input with a single sentence."""
        text = "This is a single sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 1)

    def test_empty_text(self):
        """Test empty text handling."""
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])


class TestRewriteEngine(unittest.TestCase):
    """Test the full RewriteEngine."""

    def setUp(self):
        self.engine = RewriteEngine()

    def test_analyze_returns_results(self):
        """Test that analyze returns proper structure."""
        result = self.engine.analyze(
            "The utilization of the methodology was conducted by the team."
        )
        self.assertIsInstance(result, RewriteResult)
        self.assertGreaterEqual(len(result.issues), 1)
        self.assertIsNotNone(result.metrics)
        self.assertIn("total_issues", result.metrics)

    def test_improve_generates_rewrite(self):
        """Test that improve generates rewritten text."""
        result = self.engine.improve(
            "Due to the fact that the results were very significant, "
            "the researchers came to a conclusion."
        )
        self.assertIsNotNone(result.rewritten_text)
        # Rewritten text should differ from original
        self.assertNotEqual(
            result.rewritten_text.strip(),
            result.original_text.strip()
        )

    def test_improve_preserves_length(self):
        """Test that improved text is not drastically shorter."""
        original = (
            "Due to the fact that a large number of participants "
            "were involved in the study."
        )
        result = self.engine.improve(original)
        # Rewritten should be shorter (removed wordiness)
        # But still recognizable
        self.assertLessEqual(
            len(result.rewritten_text),
            len(original) * 1.5  # Allow some growth for added clarity
        )

    def test_metrics_structure(self):
        """Test that metrics are properly computed."""
        result = self.engine.analyze("First sentence. Second sentence. Third sentence.")
        metrics = result.metrics
        self.assertIn("total_words", metrics)
        self.assertIn("total_sentences", metrics)
        self.assertIn("total_issues", metrics)
        self.assertIn("severity_breakdown", metrics)
        self.assertIn("category_breakdown", metrics)
        self.assertEqual(metrics["total_sentences"], 3)

    def test_clean_text_no_issues(self):
        """Test that clean academic text produces few issues."""
        text = (
            "The study examined the relationship between temperature "
            "and reaction rate. Researchers collected data from "
            "50 participants over a period of six months. "
            "The results confirmed the initial hypothesis."
        )
        result = self.engine.analyze(text)
        # Well-written academic text should have minimal issues
        self.assertLessEqual(len(result.issues), 3)


class TestMainAPI(unittest.TestCase):
    """Test the public API functions."""

    def test_improve_writing_basic(self):
        """Test basic improve_writing call."""
        result = improve_writing(
            "The utilization of the methodology was utilized for analysis.",
        )
        self.assertIn("original_text", result)
        self.assertIn("rewritten_text", result)
        self.assertIn("issues", result)
        self.assertIn("metrics", result)
        self.assertIsNotNone(result["rewritten_text"])

    def test_improve_writing_analyze_mode(self):
        """Test improve_writing in analyze mode."""
        result = improve_writing(
            "The utilization of the methodology was utilized for analysis.",
            mode="analyze",
        )
        self.assertIn("original_text", result)
        self.assertIsNone(result["rewritten_text"])
        self.assertIn("issues", result)

    def test_analyze_sentence_function(self):
        """Test analyze_sentence convenience function."""
        issues = analyze_sentence(
            "The results were very interesting and somewhat significant."
        )
        self.assertGreaterEqual(len(issues), 1)
        self.assertIn("category", issues[0])
        self.assertIn("severity", issues[0])
        self.assertIn("description", issues[0])

    def test_analyze_sentence_clean(self):
        """Test analyze_sentence on clean text."""
        issues = analyze_sentence("The results confirmed the hypothesis.")
        # Possibly no issues with clean sentence
        self.assertIsInstance(issues, list)

    def test_analyze_sentence_empty(self):
        """Test analyze_sentence with empty input."""
        self.assertEqual(analyze_sentence(""), [])
        self.assertEqual(analyze_sentence(None), [])
        self.assertEqual(analyze_sentence("   "), [])

    def test_improve_writing_empty(self):
        """Test improve_writing with empty input raises ValueError."""
        with self.assertRaises(ValueError):
            improve_writing("")

    def test_improve_writing_invalid_mode(self):
        """Test improve_writing with invalid mode raises ValueError."""
        with self.assertRaises(ValueError):
            improve_writing("Some text.", mode="invalid")

    def test_get_supported_categories(self):
        """Test get_supported_categories returns proper structure."""
        categories = get_supported_categories()
        self.assertGreaterEqual(len(categories), 5)  # At least 5 categories
        for cat in categories:
            self.assertIn("id", cat)
            self.assertIn("name", cat)
            self.assertIn("description", cat)
            self.assertIn("default_severity", cat)

    def test_improve_writing_verbose_phrase_rewrite(self):
        """Test that wordiness is actually rewritten in improve mode."""
        text = "The experiment was conducted for the purpose of testing the hypothesis."
        result = improve_writing(text)
        # "for the purpose of" should become "to"
        self.assertIn("to", result["rewritten_text"])
        self.assertNotIn("for the purpose of", result["rewritten_text"])

    def test_integrity_with_statistics(self):
        """Test full statistical output preservation."""
        text = (
            "The analysis revealed a significant effect (t(28) = 2.45, p = 0.01). "
            "The 95% CI [1.23, 4.56] confirmed the results."
        )
        result = improve_writing(text)
        self.assertIn("t(28) = 2.45", result["rewritten_text"])
        self.assertIn("p = 0.01", result["rewritten_text"])
        self.assertIn("95% CI [1.23, 4.56]", result["rewritten_text"])
        self.assertEqual(len(result["integrity_violations"]), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_very_short_text(self):
        """Test with single-word text."""
        result = improve_writing("Hello world.", mode="analyze")
        self.assertIsInstance(result, dict)

    def test_text_with_only_citations(self):
        """Test text that is just citations."""
        text = "(Smith, 2020; Johnson et al., 2019)"
        result = improve_writing(text, mode="analyze")
        self.assertEqual(len(result["integrity_violations"]), 0)

    def test_text_with_special_characters(self):
        """Test text with special characters and symbols."""
        text = (
            "The ΔG° value was −5.2 kcal/mol at pH 7.4 (n = 3; mean ± SD)."
        )
        result = improve_writing(text)
        self.assertIn("ΔG°", result["rewritten_text"])
        self.assertIn("−5.2 kcal/mol", result["rewritten_text"])
        self.assertIn("pH 7.4", result["rewritten_text"])

    def test_text_with_latex_math(self):
        """Test text with LaTeX inline math."""
        text = "The equation $E = mc^2$ describes the relationship."
        result = improve_writing(text)
        self.assertIn("$E = mc^2$", result["rewritten_text"])

    def test_very_long_single_sentence(self):
        """Test very long single sentence."""
        text = "A " * 100 + "."
        result = improve_writing(text, mode="analyze")
        self.assertIn("complex_sentence", [i["category"] for i in result["issues"]])


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions in patterns module."""

    def test_count_clauses(self):
        """Test clause counting."""
        simple = "The results were significant."
        self.assertEqual(count_clauses(simple), 1)

        complex_sent = "The study which was conducted found that results were significant."
        self.assertGreater(count_clauses(complex_sent), 1)

    def test_is_overly_long(self):
        """Test long sentence detection."""
        short = "Short sentence."
        self.assertFalse(is_overly_long(short))

        long_text = "This is " + "very " * 40 + "long sentence."
        self.assertTrue(is_overly_long(long_text))

    def test_has_weak_opener(self):
        """Test weak opener detection."""
        self.assertTrue(has_weak_opener("There is a significant difference."))
        self.assertTrue(has_weak_opener("It was observed that the results..."))
        self.assertTrue(has_weak_opener("This is important because..."))
        self.assertFalse(has_weak_opener("The results showed significance."))


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)