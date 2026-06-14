"""
protector.py

Ensures critical academic content is preserved during rewriting:

Protected content types:
  1. CITATIONS  - inline citations (Smith, 2020), (Author et al., 2019), [1], [2-5]
  2. REFERENCES - reference labels like [1], [2, 3], [4-7]
  3. NUMBERS    - numerical values, percentages, statistical results
  4. FORMULAE   - mathematical/scientific notation
  5. TECHNICAL_TERMS - domain-specific terminology (preserved as-is)
  6. QUOTATIONS - quoted text that should remain verbatim

The protector replaces protected spans with placeholders before rewriting,
then restores the originals after the rewrite is complete.
"""

import re
from typing import List, Tuple, Optional


class ContentProtector:
    """
    Manages placeholders for protected content during rewriting.

    Usage:
        protector = ContentProtector()
        text = protector.protect("The results (Smith et al., 2020) show p < 0.05...")
        # Now text has placeholders like <<CIT_0>>, <<NUM_1>> instead of protected spans
        modified = rewriter.rewrite(text)
        result = protector.restore(modified)
        # Restored with original citations, numbers, etc. intact
    """

    def __init__(self):
        self._placeholders: List[Tuple[str, str, int, int]] = []
        # (placeholder, original_text, start, end) - sorted by start position
        self._placeholder_counter = 0

    def protect(self, text: str) -> str:
        """
        Replace all protected content with placeholders.

        Args:
            text (str): Input academic text.

        Returns:
            str: Text with protected spans replaced by <<TYPE_N>> placeholders.
        """
        self._placeholders = []
        self._placeholder_counter = 0
        protected_spans = []

        # 1. Extract citations (highest priority - protect first)
        citations = self._extract_citations(text)
        protected_spans.extend(citations)

        # 2. Extract numbers and statistical values
        numbers = self._extract_numbers(text)
        protected_spans.extend(numbers)

        # 3. Extract quoted text
        quotations = self._extract_quotations(text)
        protected_spans.extend(quotations)

        # 4. Extract inline math/formulae
        formulae = self._extract_formulae(text)
        protected_spans.extend(formulae)

        # 5. Extract URLs
        urls = self._extract_urls(text)
        protected_spans.extend(urls)

        # Sort by position (ascending) and merge overlapping spans
        protected_spans.sort(key=lambda x: x[0])
        merged_spans = self._merge_spans(protected_spans)

        # Replace from end to start to preserve positions
        result = list(text)
        for start, end, original, ptype in reversed(merged_spans):
            placeholder = f"<<{ptype}_{self._placeholder_counter}>>"
            self._placeholder_counter += 1
            self._placeholders.append((placeholder, original, start, end))
            # Replace the span with placeholder
            result[start:end] = placeholder

        return "".join(result)

    def restore(self, text: str) -> str:
        """
        Restore all placeholders back to original protected content.

        Args:
            text (str): Text with placeholders (e.g., <<CIT_0>>, <<NUM_1>>).

        Returns:
            str: Text with original protected content restored.
        """
        # Sort by placeholder to ensure consistent replacement
        for placeholder, original, _, _ in reversed(self._placeholders):
            # Only replace if the placeholder still exists
            text = text.replace(placeholder, original)
        return text

    def get_protected_ranges(self) -> List[Tuple[int, int]]:
        """
        Get the character ranges of all protected content in the original text.

        Returns:
            list of (start, end) tuples representing protected spans.
        """
        return [(s, e) for _, _, s, e in self._placeholders]

    # ------------------------------------------------------------------
    # Extraction methods
    # ------------------------------------------------------------------

    CITATION_PATTERNS = [
        # (Smith, 2020) or (Smith et al., 2020)
        r"\([A-Z][a-zA-Z&.'\-]+(?:\s+(?:et al\.?|and\s+\w+))?\s*[,;]\s*\d{4}[a-z]?\)",
        # (Smith and Jones, 2020) or (Smith & Jones, 2020)
        r"\([A-Z][a-zA-Z.'\-]+\s+(?:and|&)\s+[A-Z][a-zA-Z.'\-]+\s*[,;]\s*\d{4}[a-z]?\)",
        # (Author et al., 2020; Author2 et al., 2021) - multiple citations
        r"\([^)]*\d{4}[a-z]?\)",
        # Smith (2020) or Smith et al. (2020)
        r"[A-Z][a-zA-Z.'\-]+\s+(?:et\s+al\.?\s+)?\(\d{4}[a-z]?\)",
        # [1], [2,3], [4-7], [1, 2, 3] style
        r"\[[\d,\s\-]+\]",
        # Author (2020, p. 123) or Author (2020, pp. 123-125)
        r"[A-Z][a-zA-Z.'\-]+\s+\(\d{4}[a-z]?,\s*(?:p|pp)\.\s*[\d\-]+\)",
    ]

    NUMBER_PATTERNS = [
        # Statistical values: p < 0.05, p = 0.01, p < .001
        r"p\s*[<>=]\s*0\.\d+",
        # t-values: t(28) = 2.45, t = 1.96
        r"t\s*\(\s*\d+\s*\)\s*=\s*-?[\d.]+",
        # F-values: F(1, 28) = 4.52
        r"F\s*\(\s*\d+\s*,\s*\d+\s*\)\s*=\s*-?[\d.]+",
        # r-values: r = 0.45, r(28) = 0.45
        r"r\s*(?:\(\s*\d+\s*\))?\s*=\s*-?0\.\d+",
        # chi-square: χ²(1) = 3.84
        r"χ²?\s*\(\s*\d+\s*\)\s*=\s*-?[\d.]+",
        # Mean ± SD: M = 4.52, SD = 1.23
        r"M\s*=\s*[\d.]+(?:\s*±\s*[\d.]+)?",
        r"SD\s*=\s*[\d.]+",
        # R² values
        r"R²?\s*=\s*0\.\d+",
        # β values: β = 0.32, β = -.24
        r"β\s*=\s*-?0?\.\d+",
        # Percentages: 45%, 45.2%
        r"\d+\.?\d*\s*%",
        # Confidence intervals: 95% CI [1.23, 4.56]
        r"\d+\s*%\s*CI\s*\[[\d.\s,\-]+\]",
        # Generic decimal numbers that are standalone (≥3 digits or have decimal)
        r"(?<!\w)-?\d+\.\d{2,}(?!\w)",
        # Large numbers (thousands+)
        r"(?<!\w)\d{4,}(?!\w)",
        # Ranges: 10-20, 100-200
        r"(?<!\w)\d{2,}\s*[-–—]\s*\d{2,}(?!\w)",
        # Units: 10 mg, 5.2 mL, 37°C, 100 mM
        r"\d+\.?\d*\s*(?:mg|mL|ml|μL|µL|g|kg|°C|°F|K|mM|μM|µM|nM|mm|cm|nm|μm|µm|h|min|s|Hz|kHz|MPa|kPa|Pa)\.?\b",
    ]

    QUOTATION_PATTERNS = [
        # Double-quoted text: "like this"
        r'"[^"]{3,}"',
        # Single-quoted text: 'like this'
        r"'[^']{3,}'",
        # Block quotation markers (indented text)
        r"(?m)^\s{4,}[^\n]+",  # lines starting with 4+ spaces
    ]

    FORMULA_PATTERNS = [
        r"\$\$[^$]+\$\$",  # LaTeX display math: $$...$$
        r"\$[^$]+\$",       # LaTeX inline math: $...$
        r"\\\([^)]+\\\)",   # LaTeX: \(...\)
        r"\\\[[^\]]+\\\]",  # LaTeX: \[...\]
        r"\bE\s*=\s*mc\^2\b",
        r"\b[a-zA-Z]\s*=\s*[a-zA-Z][^.\s]*",
    ]

    URL_PATTERNS = [
        r"https?://[^\s,;:.!?)]+(?:\.[^\s,;:.!?)]+)*",
        r"doi:\s*10\.\d{4,}/[^\s,;:.!?)]+",
        r"www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s,;:.!?)]*)?",
    ]

    # Technical terms that must NOT be modified (domain-specific)
    PROTECTED_TERMS = [
        "in vitro", "in vivo", "ex vivo", "in situ", "in silico",
        "de novo", "ad hoc", "ad libitum", "post hoc",
        "a priori", "a posteriori", "per se", "per annum",
        "inter alia", "et al.", "i.e.", "e.g.", "cf.", "vs.",
        "via", "vice versa",
    ]

    def _extract_citations(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Extract citation spans from text."""
        spans = []
        for pattern in self.CITATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                start, end = match.start(), match.end()
                original = match.group(0)
                # Avoid duplicates (overlapping matches)
                if not any(s <= start < e or s < end <= e for s, e, _, _ in spans):
                    spans.append((start, end, original, "CIT"))
        return spans

    def _extract_numbers(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Extract numerical and statistical values."""
        spans = []
        for pattern in self.NUMBER_PATTERNS:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                original = match.group(0)
                # Avoid duplicates
                if not any(s <= start < e or s < end <= e for s, e, _, _ in spans):
                    spans.append((start, end, original, "NUM"))
        return spans

    def _extract_quotations(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Extract quoted text spans."""
        spans = []
        for pattern in self.QUOTATION_PATTERNS:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                original = match.group(0)
                if not any(s <= start < e or s < end <= e for s, e, _, _ in spans):
                    spans.append((start, end, original, "QOT"))
        return spans

    def _extract_formulae(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Extract mathematical formulae."""
        spans = []
        for pattern in self.FORMULA_PATTERNS:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                original = match.group(0)
                if not any(s <= start < e or s < end <= e for s, e, _, _ in spans):
                    spans.append((start, end, original, "FML"))
        return spans

    def _extract_urls(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Extract URLs and DOIs."""
        spans = []
        for pattern in self.URL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.start(), match.end()
                original = match.group(0)
                if not any(s <= start < e or s < end <= e for s, e, _, _ in spans):
                    spans.append((start, end, original, "URL"))
        return spans

    def _merge_spans(self, spans: List[Tuple[int, int, str, str]]) -> List[Tuple[int, int, str, str]]:
        """
        Merge overlapping or adjacent spans, keeping the outermost.

        Args:
            spans: List of (start, end, original, type) tuples.

        Returns:
            List of merged (start, end, original, type) tuples.
        """
        if not spans:
            return []

        # Sort by start, then by end (descending to prefer longer spans)
        spans.sort(key=lambda x: (x[0], -x[1]))
        merged = [spans[0]]

        for span in spans[1:]:
            prev_start, prev_end, prev_orig, prev_type = merged[-1]
            curr_start, curr_end, curr_orig, curr_type = span

            if curr_start <= prev_end:
                # Overlapping: keep the longer span
                new_start = min(prev_start, curr_start)
                new_end = max(prev_end, curr_end)
                # Prefer citation type if either is a citation
                if prev_type == "CIT" or curr_type == "CIT":
                    new_type = "CIT"
                else:
                    new_type = prev_type
                # Keep the original text of the longer span
                new_orig = prev_orig if (prev_end - prev_start) >= (curr_end - curr_start) else curr_orig
                merged[-1] = (new_start, new_end, new_orig, new_type)
            else:
                merged.append(span)

        return merged

    def is_protected(self, text: str) -> bool:
        """
        Check if text contains any protected content (citations, numbers, etc.).

        Args:
            text (str): Input text.

        Returns:
            bool: True if any protected content is found.
        """
        for pattern in self.CITATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        for pattern in self.NUMBER_PATTERNS:
            if re.search(pattern, text):
                return True
        for pattern in self.QUOTATION_PATTERNS:
            if re.search(pattern, text):
                return True
        for pattern in self.FORMULA_PATTERNS:
            if re.search(pattern, text):
                return True
        for pattern in self.URL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def verify_integrity(self, original: str, rewritten: str) -> List[str]:
        """
        Verify that all protected content survived the rewrite intact.

        Args:
            original (str): Original input text.
            rewritten (str): Rewritten output text.

        Returns:
            list of str: List of any integrity violations found.
        """
        violations = []
        # Re-extract protected content from original
        original_protector = ContentProtector()
        original_protector.protect(original)
        for placeholder, original_text, s, e in original_protector._placeholders:
            if original_text not in rewritten:
                violations.append(
                    f"Protected content lost: '{original_text[:50]}...' "
                    f"(type: {placeholder.split('_')[0].strip('<')})"
                )
        return violations


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def protect_text(text: str) -> Tuple[str, ContentProtector]:
    """
    Protect citations, numbers, and technical content in a text.

    Args:
        text (str): Input academic text.

    Returns:
        tuple: (protected_text, ContentProtector instance for restoration)
    """
    protector = ContentProtector()
    protected = protector.protect(text)
    return protected, protector


def restore_text(protected_text: str, protector: ContentProtector) -> str:
    """
    Restore protected content after rewriting.

    Args:
        protected_text (str): Text with placeholders from protector.
        protector (ContentProtector): The protector instance used.

    Returns:
        str: Text with original protected content restored.
    """
    return protector.restore(protected_text)


def verify_protection(original: str, rewritten: str) -> List[str]:
    """
    Verify that all protected content was preserved after rewriting.

    Args:
        original (str): Original text.
        rewritten (str): Rewritten text.

    Returns:
        list of str: List of violations (empty if all content preserved).
    """
    p = ContentProtector()
    return p.verify_integrity(original, rewritten)