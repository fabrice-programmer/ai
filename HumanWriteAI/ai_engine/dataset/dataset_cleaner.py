"""
dataset_cleaner.py

Cleans loaded text data:
  - Normalise whitespace and strip HTML tags
  - Remove empty/too-short documents
  - Remove duplicate texts (exact and near-duplicate via fuzzy ratio)
  - Integrates with ai_engine/preprocessing/cleaner.py
"""

import re
import hashlib
from difflib import SequenceMatcher
from pathlib import Path
import sys

# Allow import from sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_engine.preprocessing.cleaner import clean_text as base_clean_text


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def strip_html(text):
    """Remove HTML/XML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def normalize_whitespace(text):
    """Collapse multiple whitespace characters into a single space."""
    return " ".join(text.split())


def clean_text(text, strip_html_tags=True):
    """
    Full cleaning pipeline for a single text string.
    Uses the project's existing base cleaner under the hood.

    Args:
        text (str): Raw text.
        strip_html_tags (bool): Whether to remove HTML tags first.

    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""

    if strip_html_tags:
        text = strip_html(text)

    text = normalize_whitespace(text)
    text = base_clean_text(text)  # from ai_engine/preprocessing/cleaner.py
    return text.strip()


# ---------------------------------------------------------------------------
# Dataset-level cleaning
# ---------------------------------------------------------------------------

def clean_dataset(data, min_length=20, strip_html_tags=True):
    """
    Apply text cleaning to every entry in a dataset list.

    Args:
        data (list of dict): Each dict must contain 'text'.
        min_length (int): Minimum character length after cleaning (skip shorter).
        strip_html_tags (bool): Whether to strip HTML tags.

    Returns:
        list of dict: Cleaned entries (without empty/short texts).
    """
    cleaned = []
    removed_count = 0

    for item in data:
        raw = item.get("text", "")
        cleaned_text = clean_text(raw, strip_html_tags=strip_html_tags)

        if len(cleaned_text) < min_length:
            removed_count += 1
            continue

        item["text"] = cleaned_text
        cleaned.append(item)

    print(f"Cleaning: kept {len(cleaned)}, removed {removed_count} (too short or empty)")
    return cleaned


# ---------------------------------------------------------------------------
# Duplicate removal
# ---------------------------------------------------------------------------

def _text_hash(text):
    """Return SHA-256 hex digest of text for exact dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def remove_exact_duplicates(data, key="text"):
    """
    Remove entries with identical text content.
    Keeps the first occurrence.

    Args:
        data (list of dict): Dataset entries.
        key (str): Dictionary key to check for duplicates.

    Returns:
        list of dict: Deduplicated entries.
    """
    seen = set()
    deduped = []
    for item in data:
        h = _text_hash(item.get(key, ""))
        if h not in seen:
            seen.add(h)
            deduped.append(item)

    removed = len(data) - len(deduped)
    print(f"Exact dedup: kept {len(deduped)}, removed {removed} duplicates")
    return deduped


def remove_near_duplicates(data, key="text", threshold=0.85):
    """
    Remove near-duplicate entries using sequence matching.
    Compares each text against all earlier kept texts;
    if similarity > threshold, the later one is dropped.

    Args:
        data (list of dict): Dataset entries.
        key (str): Dictionary key to compare.
        threshold (float): Similarity ratio (0.0 – 1.0).
                           Higher = more strict (fewer removals).

    Returns:
        list of dict: Deduplicated entries.
    """
    deduped = []
    for item in data:
        text = item.get(key, "")
        is_dup = False
        for kept in deduped:
            kept_text = kept.get(key, "")
            ratio = SequenceMatcher(None, text, kept_text).ratio()
            if ratio > threshold:
                is_dup = True
                break
        if not is_dup:
            deduped.append(item)

    removed = len(data) - len(deduped)
    print(f"Near-dedup (threshold={threshold}): kept {len(deduped)}, removed {removed} duplicates")
    return deduped


def remove_duplicates(data, key="text", near_threshold=None):
    """
    Convenience: remove exact duplicates first, then near-duplicates if threshold given.

    Args:
        data (list of dict): Dataset entries.
        key (str): Dictionary key to compare.
        near_threshold (float or None): If set, also remove near-dups above this ratio.

    Returns:
        list of dict: Deduplicated entries.
    """
    data = remove_exact_duplicates(data, key=key)
    if near_threshold is not None:
        data = remove_near_duplicates(data, key=key, threshold=near_threshold)
    return data


# ---------------------------------------------------------------------------
# Full pipeline convenience
# ---------------------------------------------------------------------------

def clean_and_deduplicate(data, min_length=20, near_threshold=None):
    """
    Run the entire cleaning + deduplication pipeline.

    Args:
        data (list of dict): Raw dataset.
        min_length (int): Minimum cleaned text length.
        near_threshold (float or None): Near-dup threshold (skip if None).

    Returns:
        list of dict: Clean, deduplicated dataset.
    """
    data = clean_dataset(data, min_length=min_length)
    data = remove_duplicates(data, near_threshold=near_threshold)
    return data


if __name__ == "__main__":
    # Quick test with sample data
    sample = [
        {"text": "Hello world!", "label": "human"},
        {"text": "  Hello   world!  ", "label": "human"},   # duplicate after clean
        {"text": "<p>AI generated text</p>", "label": "ai"},
        {"text": "Short", "label": "human"},
        {"text": "AI generated text", "label": "ai"},       # exact dup
        {"text": "AI generated text  with slight noise", "label": "ai"},
    ]
    result = clean_and_deduplicate(sample, min_length=10, near_threshold=0.85)
    for item in result:
        print(f"[{item['label']}] {item['text'][:60]}")