"""
rewriter.py

Core rewriting engine that detects awkward sentences and generates improvements.

The engine pipeline:
  1. Split text into sentences
  2. Protect citations, numbers, and technical content
  3. Apply pattern detectors to each sentence
  4. Generate improvement suggestions
  5. Restore protected content
  6. Return structured results with issues and suggestions
"""

import re
from typing import Dict, List, Optional, Tuple

from .patterns import get_all_patterns
from .protector import ContentProtector


class SentenceIssue:
    """
    Represents a detected writing issue in a single sentence.

    Attributes:
        sentence (str): The original sentence text.
        index (int): The sentence index in the original text (0-based).
        category (str): Issue category (e.g., "wordiness", "passive_voice").
        severity (str): "minor", "moderate", or "major".
        description (str): Human-readable explanation of the issue.
        suggestion (str, optional): Suggested improvement text or guidance.
    """

    def __init__(
        self,
        sentence: str,
        index: int,
        category: str,
        severity: str,
        description: str,
        suggestion: Optional[str] = None,
    ):
        self.sentence = sentence
        self.index = index
        self.category = category
        self.severity = severity
        self.description = description
        self.suggestion = suggestion

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sentence": self.sentence,
            "index": self.index,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
        }

    def __repr__(self) -> str:
        return (
            f"SentenceIssue(sentence={self.sentence[:50]!r}..., "
            f"category={self.category!r}, severity={self.severity!r})"
        )


class RewriteResult:
    """
    Result of a full rewrite operation.

    Attributes:
        original_text (str): The input text before rewriting.
        rewritten_text (str, optional): The fully improved text.
        issues (list of SentenceIssue): All detected issues.
        integrity_violations (list of str): Any protected content lost.
        metrics (dict): Summary statistics about the rewrite.
    """

    def __init__(self, original_text: str):
        self.original_text = original_text
        self.rewritten_text: Optional[str] = None
        self.issues: List[SentenceIssue] = []
        self.integrity_violations: List[str] = []
        self.metrics: Dict = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "original_text": self.original_text,
            "rewritten_text": self.rewritten_text,
            "issues": [issue.to_dict() for issue in self.issues],
            "integrity_violations": self.integrity_violations,
            "metrics": self.metrics,
        }

    def __repr__(self) -> str:
        return (
            f"RewriteResult(issues={len(self.issues)}, "
            f"rewritten={'yes' if self.rewritten_text else 'no'})"
        )


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

# Sentence boundary patterns (handles academic punctuation)
SENTENCE_BOUNDARIES = re.compile(
    r"""
    (?<=[.!?])                                                              # boundary marker
    \s+                                                                     # whitespace after
    (?=[A-Z"'(])                                                            # next sentence starts with capital
    """,
    re.VERBOSE,
)

# Abbreviation exceptions - do not split after these (regardless of case)
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "ave",
    "blvd", "rd", "dept", "vs", "fig",
    "e.g", "i.e", "cf", "etc",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "al",   # "et al."
}


def _is_abbreviation(word: str) -> bool:
    """
    Check if a word (with trailing period removed) is a known abbreviation.

    Args:
        word (str): A word token, possibly ending in '.'

    Returns:
        bool: True if the word is a known abbreviation.
    """
    # Strip trailing period
    base = word.rstrip('.').strip().lower()
    # Check known abbreviations
    if base in ABBREVIATIONS:
        return True
    # Single initial followed by period (e.g., "J." as in "J. Smith")
    if re.match(r'^[A-Za-z]\.$', word.strip()):
        return True
    return False


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences, handling academic abbreviations.

    Args:
        text (str): Input text.

    Returns:
        list of str: Sentences.
    """
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        return []

    # Split on sentence boundaries
    parts = SENTENCE_BOUNDARIES.split(text)

    # Post-process: re-join parts that were split at an abbreviation
    # e.g., "et al." followed by " Further..." should not split
    adjusted_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        # Check if this part ends with a potential abbreviation
        words = part.split()
        if words and _is_abbreviation(words[-1]):
            # This part ends with an abbreviation - the split was likely wrong
            # Merge with the next part if it exists
            if i + 1 < len(parts) and parts[i + 1].strip():
                merged = part + " " + parts[i + 1].strip()
                adjusted_parts.append(merged)
                i += 2
                continue
            else:
                adjusted_parts.append(part)
        else:
            adjusted_parts.append(part)
        i += 1

    # Filter empty strings and strip
    sentences = []
    for part in adjusted_parts:
        stripped = part.strip()
        if stripped:
            # Ensure sentence ends with period if it doesn't have terminal punctuation
            if not stripped[-1] in '.!?':
                stripped += '.'
            sentences.append(stripped)

    # If splitting produced nothing, return the whole text as one sentence
    if not sentences and text.strip():
        if not text.strip()[-1] in '.!?':
            return [text.strip() + '.']
        return [text.strip()]

    return sentences


# ---------------------------------------------------------------------------
# Rewrite engine
# ---------------------------------------------------------------------------

class RewriteEngine:
    """
    Core engine for academic writing improvement.

    Applies pattern-based detection to identify awkward sentences and
    generates actionable improvement suggestions while preserving
    citations, numbers, and scientific meaning.

    Usage:
        engine = RewriteEngine()
        result = engine.analyze("The results of the experiment were...")
        result = engine.improve("The results of the experiment were...")
    """

    def __init__(self):
        self._patterns = get_all_patterns()

    def analyze(self, text: str) -> RewriteResult:
        """
        Analyze text and detect all writing issues without rewriting.

        Args:
            text (str): Academic text to analyze.

        Returns:
            RewriteResult: Analysis results with issues but no rewritten_text.
        """
        result = RewriteResult(text)

        # Protect citations and numbers
        protector = ContentProtector()
        protected_text = protector.protect(text)

        # Split into sentences (on protected text)
        sentences = split_sentences(protected_text)

        # Analyze each sentence against all patterns
        for sent_idx, sentence in enumerate(sentences):
            stripped = sentence.strip()
            if not stripped:
                continue

            for pattern in self._patterns:
                try:
                    detected = pattern["detect_func"](stripped)
                except Exception:
                    detected = False

                if detected:
                    # Generate suggestion
                    try:
                        suggestion = pattern["suggest_func"](stripped)
                    except Exception:
                        suggestion = None

                    # Restore protected content within this sentence's suggestion
                    if suggestion:
                        suggestion = protector.restore(suggestion)

                    issue = SentenceIssue(
                        sentence=protector.restore(stripped),
                        index=sent_idx,
                        category=pattern["category"],
                        severity=pattern["severity"],
                        description=pattern["description"],
                        suggestion=suggestion,
                    )
                    result.issues.append(issue)

        # Calculate metrics
        result.metrics = self._compute_metrics(result, sentences)
        result.integrity_violations = []

        return result

    def improve(self, text: str) -> RewriteResult:
        """
        Analyze text and generate improved rewriting.

        Applies all suggestions to produce a rewritten version, then
        verifies that no protected content was altered.

        Args:
            text (str): Academic text to improve.

        Returns:
            RewriteResult: Full analysis with rewritten_text.
        """
        result = self.analyze(text)

        if not result.issues:
            # No issues found - return the original text
            result.rewritten_text = text
            result.integrity_violations = []
            return result

        # Apply improvements sentence by sentence
        protector = ContentProtector()
        protected_text = protector.protect(text)
        sentences = split_sentences(protected_text)

        # Group issues by sentence index
        issues_by_sentence: Dict[int, List[SentenceIssue]] = {}
        for issue in result.issues:
            sent_idx = issue.index
            if sent_idx not in issues_by_sentence:
                issues_by_sentence[sent_idx] = []
            issues_by_sentence[sent_idx].append(issue)

        # Build rewritten text
        rewritten_sentences = []
        for sent_idx, sentence in enumerate(sentences):
            if sent_idx in issues_by_sentence:
                improved = self._apply_suggestions(
                    sentence, issues_by_sentence[sent_idx]
                )
                rewritten_sentences.append(improved)
            else:
                rewritten_sentences.append(sentence)

        # Reconstruct full text
        rewritten_protected = " ".join(rewritten_sentences)
        result.rewritten_text = protector.restore(rewritten_protected)

        # Verify integrity of protected content
        result.integrity_violations = protector.verify_integrity(
            result.original_text, result.rewritten_text
        )

        return result

    def _apply_suggestions(
        self, sentence: str, issues: List[SentenceIssue]
    ) -> str:
        """
        Apply suggestion transformations to a sentence.

        Tries to apply direct rewrites from suggestion functions.
        If no direct rewrite is available, returns the original sentence.

        Args:
            sentence (str): The protected (placeholder) sentence.
            issues (list of SentenceIssue): Issues detected in this sentence.

        Returns:
            str: The improved sentence (still with placeholders).
        """
        # Start with the original sentence
        current = sentence

        for issue in issues:
            suggestion = issue.suggestion
            if not suggestion:
                continue

            # If the suggestion looks like a direct rewrite (replaces text),
            # try to apply it. Otherwise, keep the original.
            # Direct rewrites are concrete replacements, not just advice.
            if self._is_direct_rewrite(suggestion, current):
                # Suggestion replaces the full sentence
                if self._is_full_sentence_suggestion(suggestion):
                    current = suggestion
                else:
                    # Try to apply the suggestion as a targeted replacement
                    current = self._apply_targeted_rewrite(
                        current, issue.category, suggestion
                    )

        return current

    def _is_direct_rewrite(self, suggestion: str, original: str) -> bool:
        """
        Check if a suggestion is a direct rewrite (not just advice).

        Direct rewrites don't contain words like "consider", "replace", "use".
        """
        advice_markers = [
            "consider", "replace", "avoid", "try using", "instead of",
            "aim for", "identify", "rephrase",
        ]
        lower_sug = suggestion.lower()
        for marker in advice_markers:
            if marker in lower_sug[:50]:  # Check within first 50 chars
                return False
        return True

    def _is_full_sentence_suggestion(self, suggestion: str) -> bool:
        """Check if a suggestion is a complete sentence replacement."""
        # A full sentence starts with capital (or number) and has meaningful length
        stripped = suggestion.strip()
        if len(stripped) < 10:
            return False
        return bool(re.match(r'^[A-Z"0-9(]', stripped))

    def _apply_targeted_rewrite(
        self, sentence: str, category: str, suggestion: str
    ) -> str:
        """
        Apply a targeted rewrite within a sentence.

        For categories where we have direct pattern->replacement mappings,
        we use the pattern functions.
        """
        if category == "wordiness":
            from .patterns import _suggest_wordiness
            rewrite = _suggest_wordiness(sentence)
            return rewrite if rewrite else sentence

        elif category == "redundancy":
            from .patterns import _suggest_redundancy_fix
            rewrite = _suggest_redundancy_fix(sentence)
            return rewrite if rewrite else sentence

        elif category == "nominalization":
            from .patterns import _suggest_nominalization
            rewrite = _suggest_nominalization(sentence)
            return rewrite if rewrite else sentence

        # For other categories, we return the sentence unchanged
        # (suggestions are advisory, not direct rewrites)
        return sentence

    def _compute_metrics(
        self, result: RewriteResult, sentences: List[str]
    ) -> Dict:
        """
        Compute summary metrics for the analysis.

        Args:
            result (RewriteResult): The analysis result (for issue data).
            sentences (list of str): Split sentences (protected).

        Returns:
            dict: Summary statistics.
        """
        total_sentences = len(sentences)
        total_issues = len(result.issues)
        sentences_with_issues = len(set(issue.index for issue in result.issues))
        words = result.original_text.split()
        total_words = len(words)

        # Severity breakdown
        severity_counts = {"minor": 0, "moderate": 0, "major": 0}
        category_counts: Dict[str, int] = {}
        for issue in result.issues:
            severity = issue.severity
            if severity in severity_counts:
                severity_counts[severity] += 1

            cat = issue.category
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

        # Readability estimate (Flesch Reading Ease-like simple version)
        avg_words_per_sentence = total_words / max(total_sentences, 1)

        # Issue density
        issue_density = total_issues / max(total_words, 1) * 100  # per 100 words

        return {
            "total_words": total_words,
            "total_sentences": total_sentences,
            "total_issues": total_issues,
            "sentences_with_issues": sentences_with_issues,
            "avg_sentence_length_words": round(avg_words_per_sentence, 1),
            "issue_density_per_100_words": round(issue_density, 2),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
        }


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def analyze_text(text: str) -> Dict:
    """
    Analyze text and return writing quality issues as a dict.

    Args:
        text (str): Academic text to analyze.

    Returns:
        dict: Analysis results in JSON-serializable format.
    """
    engine = RewriteEngine()
    result = engine.analyze(text)
    return result.to_dict()


def improve_text(text: str) -> Dict:
    """
    Analyze and improve text, returning full results with rewritten version.

    Args:
        text (str): Academic text to improve.

    Returns:
        dict: Full results with rewritten_text in JSON-serializable format.
    """
    engine = RewriteEngine()
    result = engine.improve(text)
    return result.to_dict()