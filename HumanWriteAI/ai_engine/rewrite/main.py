"""
main.py

Public API for the rewrite module.

Provides the top-level functions that consumers of this module should use.

Functions:
    improve_writing(text, mode="improve") -> dict
        Analyze and/or improve academic writing quality.

    analyze_sentence(sentence) -> list of dict
        Analyze a single sentence for writing issues.

    get_supported_categories() -> list of dict
        List all supported issue categories with descriptions.

Usage:
    from ai_engine.rewrite import improve_writing, analyze_sentence

    # Full text improvement
    result = improve_writing(
        "The utilization of the methodology was conducted by the researchers for the purpose of analyzing the data."
    )
    print(result["issues"])
    print(result["rewritten_text"])
"""

from typing import Dict, List

from .rewriter import RewriteEngine, SentenceIssue, RewriteResult


def improve_writing(text: str, mode: str = "improve", **kwargs) -> Dict:
    """
    Analyze and improve academic writing quality.

    Supports two modes:
      - "analyze":  Detect issues only, return analysis without rewriting.
      - "improve":  Detect issues AND generate rewritten text (default).

    Args:
        text (str): The academic text to analyze/improve.
        mode (str): Operation mode - "analyze" or "improve" (default: "improve").

    Returns:
        dict: Result with the following keys:
            - "original_text" (str): The input text.
            - "rewritten_text" (str, optional): Improved text (only in "improve" mode).
            - "issues" (list of dict): Each detected issue with:
                - "sentence": The original sentence.
                - "index": 0-based sentence position.
                - "category": Issue category name.
                - "severity": "minor", "moderate", or "major".
                - "description": Human-readable issue explanation.
                - "suggestion": Improvement suggestion or rewrite.
            - "integrity_violations" (list of str): Any protected content losses.
            - "metrics" (dict): Summary statistics.

    Raises:
        ValueError: If text is empty or mode is invalid.

    Example:
        >>> result = improve_writing(
        ...     "The results of the experiment were analyzed by the team.",
        ...     mode="analyze"
        ... )
        >>> len(result["issues"])
        2
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input text must be a non-empty string.")

    if not text.strip():
        raise ValueError("Input text is empty after stripping whitespace.")

    if mode not in ("analyze", "improve"):
        raise ValueError(
            f"Invalid mode '{mode}'. Must be 'analyze' or 'improve'."
        )

    engine = RewriteEngine()

    if mode == "analyze":
        result = engine.analyze(text)
    else:
        result = engine.improve(text)

    return result.to_dict()


def analyze_sentence(sentence: str) -> List[Dict]:
    """
    Analyze a single sentence for writing quality issues.

    This is a convenience function for per-sentence analysis.
    Returns the list of issues directly (without full metrics).

    Args:
        sentence (str): A single sentence to analyze.

    Returns:
        list of dict: Detected issues, each with:
            - "category": Issue category name.
            - "severity": "minor", "moderate", or "major".
            - "description": Human-readable explanation.
            - "suggestion": Improvement suggestion.

    Example:
        >>> issues = analyze_sentence(
        ...     "The utilization of the new methodology was employed by the researchers."
        ... )
        >>> len(issues)
        2
        >>> issues[0]["category"]
        'wordiness'
    """
    if not sentence or not isinstance(sentence, str):
        return []

    if not sentence.strip():
        return []

    engine = RewriteEngine()
    result = engine.analyze(sentence)

    # Return just the issue list, simplified
    simplified = []
    for issue in result.issues:
        simplified.append({
            "category": issue.category,
            "severity": issue.severity,
            "description": issue.description,
            "suggestion": issue.suggestion,
        })

    return simplified


def get_supported_categories() -> List[Dict]:
    """
    Get a list of all supported writing issue categories.

    Returns:
        list of dict: Each category with:
            - "id": Machine-readable category identifier.
            - "name": Human-readable category name.
            - "description": What kind of issues this detects.
            - "severity": Default severity level.

    Example:
        >>> cats = get_supported_categories()
        >>> [c["id"] for c in cats]
        ['wordiness', 'passive_voice', 'vague_language', ...]
    """
    from .patterns import get_all_patterns

    categories = {}
    for pattern in get_all_patterns():
        cat_id = pattern["category"]
        cat_desc = pattern["description"]
        cat_sev = pattern["severity"]

        if cat_id not in categories:
            # Generate a readable name from the id
            name = cat_id.replace("_", " ").title()
            categories[cat_id] = {
                "id": cat_id,
                "name": name,
                "description": cat_desc,
                "default_severity": cat_sev,
            }

    return list(categories.values())