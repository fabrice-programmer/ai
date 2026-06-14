"""
patterns.py

Defines pattern categories and detection rules for academic writing issues.

Each pattern is a dict with:
  - category: str - Issue category name
  - description: str - Human-readable description
  - severity: str - "minor" | "moderate" | "major"
  - detect_func: callable(sentence) -> bool - Detection function
  - suggest_func: callable(sentence, protected) -> str - Suggestion generator

Pattern categories:
  1. WORDINESS - Redundant or overly verbose phrasing
  2. NOMINALIZATION - Overuse of nouns instead of verbs
  3. PASSIVE_MISUSE - Unnecessary passive constructions
  4. WEAK_VERBS - Overuse of "to be", "to have", "to do" as main verbs
  5. VAGUE_LANGUAGE - Imprecise or hedging language
  6. REDUNDANCY - Repeated meaning or tautology
  7. COMPLEX_SENTENCE - Overly long or convoluted sentences
  8. COLLOQUIALISM - Informal or non-academic phrasing
"""

import re

# ---------------------------------------------------------------------------
# Wordiness patterns (verbose phrases → concise alternatives)
# ---------------------------------------------------------------------------

WORDY_PHRASES = [
    # (regex pattern, suggestion template)
    (r"\b(a large number of|a great deal of|numerous)\b", "many"),
    (r"\b(a majority of)\b", "most"),
    (r"\b(a small number of)\b", "few"),
    (r"\b(are able to|is able to)\b", "can"),
    (r"\b(as a result of)\b", "because of"),
    (r"\b(at the present time|at this point in time|currently)\b", "currently"),  # keep if needed
    (r"\b(concerning the matter of)\b", "about"),
    (r"\b(due to the fact that|owing to the fact that)\b", "because"),
    (r"\b(for the purpose of)\b", "to"),
    (r"\b(have the ability to|has the ability to|had the ability to)\b", "can"),
    (r"\b(in a (manner|way) that)\b", "so that"),
    (r"\b(in order to)\b", "to"),
    (r"\b(in the event that)\b", "if"),
    (r"\b(in the vicinity of)\b", "near"),
    (r"\b(irregardless of)\b", "regardless of"),
    (r"\b(it is (important|necessary|essential|crucial|imperative) that)\b", "must"),
    (r"\b(on a (daily|weekly|monthly|yearly) basis)\b", lambda m: m.group(1) + "ly"),
    (r"\b(prior to|previous to)\b", "before"),
    (r"\b(subsequent to)\b", "after"),
    (r"\b(the reason why is that)\b", "because"),
    (r"\b(utilize|utilization)\b", "use"),
    (r"\b(with the exception of)\b", "except"),
]

# ---------------------------------------------------------------------------
# Nominalization patterns (nouns formed from verbs → stronger verbs)
# ---------------------------------------------------------------------------

NOMINALIZATION_SUFFIXES = [
    r"\b\w+tion\b",      # e.g., "investigation" → "investigate"
    r"\b\w+ment\b",      # e.g., "establishment" → "establish"
    r"\b\w+ance\b",      # e.g., "performance" → "perform"
    r"\b\w+ence\b",      # e.g., "existence" → "exist"
    r"\b\w+ity\b",       # e.g., "productivity" → "produce"
    r"\b\w+ness\b",      # e.g., "effectiveness" → "effective" (adjective)
]

NOMINALIZATION_PHRASES = [
    (r"\b(performs?|performed|performing)\s+an\s+analysis\s+of\b", "analyze"),
    (r"\b(conducts?|conducted|conducting)\s+an\s+analysis\s+of\b", "analyze"),
    (r"\b(provides?|provided|providing)\s+a\s+(description|discussion)\s+of\b", lambda m: "describe" if m.group(2) == "description" else "discuss"),
    (r"\b(makes?|made|making)\s+a\s+(comparison|determination|decision|assessment)\b", lambda m: {"comparison": "compare", "determination": "determine", "decision": "decide", "assessment": "assess"}.get(m.group(2), m.group(2))),
    (r"\b(came|comes?|coming)\s+to\s+a\s+conclusion\b", "conclude"),
    (r"\b(gives?|gave|giving)\s+consideration\s+to\b", "consider"),
    (r"\b(has|have|had|has had)\s+(an|the)\s+effect\s+on\b", "affects"),
    (r"\b(takes?|took|taking)\s+into\s+consideration\b", "consider"),
    (r"\b(undertakes?|undertook|undertaking)\s+an\s+investigation\b", "investigate"),
]

# ---------------------------------------------------------------------------
# Passive voice misuse (unnecessary "by" agent + passive)
# ---------------------------------------------------------------------------

# Simple check: "was/were/has been/have been/had been + past participle + by"
PASSIVE_PATTERN = re.compile(
    r"\b(was|were|has been|have been|had been|is being|are being|was being|were being)\s+"
    r"(\w+ed|(\w+en))\b"
    r"(\s+by\b)?",
    re.IGNORECASE,
)

# Academic passive that SHOULD be kept (common in methods sections)
# These are generally acceptable in academic writing
ACCEPTABLE_PASSIVE_CONTEXTS = [
    "was conducted",
    "was performed",
    "was carried out",
    "was measured",
    "was calculated",
    "was analyzed",
    "was collected",
    "was obtained",
    "was divided",
    "was incubated",
    "was centrifuged",
    "was extracted",
    "was purified",
    "was synthesized",
    "was prepared",
    "was dissolved",
    "was suspended",
    "was maintained",
    "was evaluated",
    "was assessed",
    "was estimated",
    "was observed",
    "was recorded",
    "was noted",
    "was found",          # found to be...
    "was shown",          # shown in Figure...
    "was demonstrated",
    "was investigated",
    "was examined",
    "was studied",
    "was considered",
    "was regarded",
    "was defined",
    "was classified",
    "was characterized",
    "were conducted",
    "were performed",
    "were carried out",
    "were measured",
    "were calculated",
    "were analyzed",
    "were collected",
    "were obtained",
    "were divided",
    "were incubated",
    "were centrifuged",
    "were extracted",
    "were purified",
    "were synthesized",
    "were prepared",
    "were dissolved",
    "were suspended",
    "were maintained",
    "were evaluated",
    "were assessed",
    "were estimated",
    "were observed",
    "were recorded",
    "were noted",
    "were found",
    "were shown",
    "were demonstrated",
    "were investigated",
    "were examined",
    "were studied",
    "were considered",
    "were regarded",
    "were defined",
    "were classified",
    "were characterized",
    "have been conducted",
    "have been performed",
    "have been reported",
    "have been described",
    "have been identified",
    "has been shown",
    "has been demonstrated",
    "has been reported",
    "has been described",
    "has been suggested",
    "has been proposed",
    "has been associated",
    "has been linked",
    "has been observed",
    "has been found",
]

# ---------------------------------------------------------------------------
# Weak verb patterns ("is", "are", "was", "were" + adjective/past participle
# where a stronger verb would work)
# ---------------------------------------------------------------------------

WEAK_VERB_PATTERNS = [
    (r"\bis\s+(relevant|significant|important|critical|crucial)\s+(to|for)\b",
     "matters to / is critical for"),
    (r"\bare\s+(relevant|significant|important|critical|crucial)\s+(to|for)\b",
     "matter to / are critical for"),
    (r"\bis\s+consistent\s+with\b", "aligns with / matches"),
    (r"\bare\s+consistent\s+with\b", "align with / match"),
    (r"\bis\s+indicative\s+of\b", "indicates"),
    (r"\bare\s+indicative\s+of\b", "indicate"),
    (r"\bis\s+responsible\s+for\b", "drives / causes"),
    (r"\bare\s+responsible\s+for\b", "drive / cause"),
    (r"\b(is|was)\s+defined\s+as\b", "is / was defined as"),  # keep passive if standard
    (r"\b(are|were)\s+defined\s+as\b", "are / were defined as"),
]

# ---------------------------------------------------------------------------
# Vague / hedging language (overuse of weak hedges)
# ---------------------------------------------------------------------------

HEDGING_WORDS = [
    r"\b(very|quite|rather|somewhat|fairly|pretty)\b",
    r"\b(a bit|a little bit)\b",
    r"\b(kind of|sort of)\b",
]

VAGUE_NOUNS = [
    r"\b(thing|stuff|aspect|factor|area|type|kind|sort)\b",
]

VAGUE_ADJECTIVES = [
    r"\b(good|bad|nice|great|big|small|interesting|important)\b",
]

# ---------------------------------------------------------------------------
# Redundancy / tautology patterns
# ---------------------------------------------------------------------------

REDUNDANT_PHRASES = [
    (r"\b(advance (planning|notice|warning))\b", "planning / notice / warning"),
    (r"\b(combine together|join together)\b", "combine / join"),
    (r"\b(consensus of opinion)\b", "consensus"),
    (r"\b(end result|final result)\b", "result"),
    (r"\b(estimated at about)\b", "estimated at"),
    (r"\b(foreign imports)\b", "imports"),
    (r"\b(future plans)\b", "plans"),
    (r"\b(past history|past experience)\b", "history / experience"),
    (r"\b(plan ahead)\b", "plan"),
    (r"\b(revert back)\b", "revert"),
    (r"\b(repeat again)\b", "repeat"),
    (r"\b(sudden crisis)\b", "crisis"),
    (r"\b(true facts)\b", "facts"),
    (r"\b(usual custom)\b", "custom"),
    (r"\b(whether or not)\b", "whether"),
    (r"\b(and also)\b", "and"),
    (r"\b(and etc\.|etc\. etc\.)\b", "etc."),
    (r"\b(each and every)\b", "each / every"),
    (r"\b(first and foremost)\b", "first"),
    (r"\b(free gift)\b", "gift"),
]

# ---------------------------------------------------------------------------
# Colloquial / non-academic phrasing
# ---------------------------------------------------------------------------

COLLOQUIAL_PATTERNS = [
    (r"\b(a lot of|lots of)\b", "many / several / numerous"),
    (r"\b(a while|a long time)\b", "a period / an extended period"),
    (r"\b(all over)\b", "throughout / across"),
    (r"\b(basically|essentially)\b", "→ omit or be precise"),
    (r"\b(big deal)\b", "significant / important"),
    (r"\b(couple of)\b", "two / several"),
    (r"\b(get|got|gotten)\b", "obtain / acquire / become / receive"),
    (r"\b(goes against)\b", "contradicts"),
    (r"\b(hang of it)\b", "mastered / understood"),
    (r"\b(kids)\b", "children"),
    (r"\b(look at)\b", "examine / consider"),
    (r"\b(make up)\b", "constitute / compose"),
    (r"\b(more and more)\b", "increasingly"),
    (r"\b(put off)\b", "postpone / delay"),
    (r"\b(set up)\b", "establish / configure"),
    (r"\b(take a look at)\b", "examine"),
    (r"\b(take place)\b", "occur / happen"),
    (r"\b(think about|think of)\b", "consider"),
    (r"\b(way of thinking)\b", "paradigm / perspective"),
    (r"\b(what if)\b", "consider the possibility that"),
    (r"\b(deal with)\b", "address / handle"),
    (r"\b(in the long run)\b", "ultimately / over time"),
]

# ---------------------------------------------------------------------------
# Compound / complex sentence detector
# ---------------------------------------------------------------------------

# Sentences with excessive clause count
MAX_CLAUSES = 3  # More than 3 clauses suggests complexity issue

# Clause boundary markers
CLAUSE_MARKS = [
    r"\b(which|that|who|whom|whose)\b",
    r"\b(although|though|while|whereas)\b",
    r"\b(because|since|as)\b",
    r"\b(if|unless|whether)\b",
    r"\b(when|where|whenever|wherever)\b",
    r"\b(after|before|until|while)\b",
    r"\b(so that|in order that)\b",
    r"\b, (and|but|or|yet|so)\b",
    r"\b(, |;)which\b",
]


def count_clauses(sentence):
    """
    Estimate the number of clauses in a sentence.

    Args:
        sentence (str): Input sentence.

    Returns:
        int: Estimated clause count.
    """
    count = 1  # At least one main clause
    for pattern in CLAUSE_MARKS:
        matches = re.findall(pattern, sentence, re.IGNORECASE)
        count += len(matches)
    return count


def is_overly_long(sentence, max_words=40):
    """
    Check if a sentence is overly long (word count heuristic).

    Args:
        sentence (str): Input sentence.
        max_words (int): Maximum recommended word count.

    Returns:
        bool: True if sentence exceeds max_words.
    """
    words = sentence.split()
    return len(words) > max_words


# ---------------------------------------------------------------------------
# Sentence opening variety (avoid starting too many sentences the same way)
# ---------------------------------------------------------------------------

WEAK_OPENERS = [
    r"^It is",
    r"^It was",
    r"^There is",
    r"^There are",
    r"^There was",
    r"^There were",
    r"^This is",
    r"^This was",
    r"^These are",
    r"^These were",
]


def has_weak_opener(sentence):
    """
    Check if sentence starts with a weak expletive construction.

    Args:
        sentence (str): Input sentence (first sentence in a passage).

    Returns:
        bool: True if sentence starts with "There is/are/was/were" or "It is/was".
    """
    for pattern in WEAK_OPENERS:
        if re.match(pattern, sentence.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# High-level detection interface
# ---------------------------------------------------------------------------

def get_all_patterns():
    """
    Return all pattern detectors as a list of dicts.

    Each dict has:
      - category: str
      - description: str
      - severity: str ("minor" | "moderate" | "major")
      - detect_func: callable(sentence) -> (bool, str|None, str|None)
            Returns (is_issue, suggestion, category_detail)
    """
    patterns = []

    # 1. Wordiness patterns
    patterns.append({
        "category": "wordiness",
        "description": "Verbose or redundant phrasing that can be made more concise",
        "severity": "moderate",
        "detect_func": _detect_wordiness,
        "suggest_func": _suggest_wordiness,
    })

    # 2. Nominalization patterns
    patterns.append({
        "category": "nominalization",
        "description": "Nouns derived from verbs that weaken sentence strength",
        "severity": "moderate",
        "detect_func": _detect_nominalization_phrases,
        "suggest_func": _suggest_nominalization,
    })

    # 3. Passive voice misuse
    patterns.append({
        "category": "passive_voice",
        "description": "Unnecessary passive construction (active voice is more direct)",
        "severity": "minor",
        "detect_func": _detect_unnecessary_passive,
        "suggest_func": _suggest_active_voice,
    })

    # 4. Weak verb usage
    patterns.append({
        "category": "weak_verb",
        "description": "Weak verbs like 'is/was' where a stronger action verb would improve clarity",
        "severity": "moderate",
        "detect_func": _detect_weak_verb,
        "suggest_func": _suggest_stronger_verb,
    })

    # 5. Vague language
    patterns.append({
        "category": "vague_language",
        "description": "Hedging or imprecise language that weakens academic writing",
        "severity": "moderate",
        "detect_func": _detect_vague_language,
        "suggest_func": _suggest_precise_language,
    })

    # 6. Redundancy
    patterns.append({
        "category": "redundancy",
        "description": "Tautological or redundant phrases",
        "severity": "minor",
        "detect_func": _detect_redundancy,
        "suggest_func": _suggest_redundancy_fix,
    })

    # 7. Colloquialism
    patterns.append({
        "category": "colloquialism",
        "description": "Informal or conversational phrasing inappropriate for academic writing",
        "severity": "moderate",
        "detect_func": _detect_colloquialism,
        "suggest_func": _suggest_formal_alternative,
    })

    # 8. Complex / long sentence
    patterns.append({
        "category": "complex_sentence",
        "description": "Overly long or multi-clause sentence that may hinder readability",
        "severity": "minor",
        "detect_func": _detect_complex_sentence,
        "suggest_func": _suggest_simpler_sentence,
    })

    # 9. Weak opener
    patterns.append({
        "category": "weak_opener",
        "description": "Sentence begins with expletive construction (There is/are, It is)",
        "severity": "minor",
        "detect_func": _detect_weak_opener,
        "suggest_func": _suggest_stronger_opener,
    })

    return patterns


# ---------------------------------------------------------------------------
# Detection implementations
# ---------------------------------------------------------------------------

def _detect_wordiness(sentence):
    """Detect verbose phrasing in a sentence."""
    for pattern, _ in WORDY_PHRASES:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_wordiness(sentence):
    """Suggest removing wordy phrases."""
    result = sentence
    for pattern, replacement in WORDY_PHRASES:
        if callable(replacement):
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        else:
            # Case-insensitive replace, preserving case of first match character
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    if result != sentence:
        return result
    return None


def _detect_nominalization_phrases(sentence):
    """Detect nominalization patterns."""
    for pattern, _ in NOMINALIZATION_PHRASES:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_nominalization(sentence):
    """Suggest replacing nominalizations with verb forms."""
    result = sentence
    for pattern, replacement in NOMINALIZATION_PHRASES:
        if callable(replacement):
            result = re.sub(pattern, replacement(result) if callable(replacement) else replacement, result, flags=re.IGNORECASE)
        else:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    if result != sentence:
        return result
    return None


def _detect_unnecessary_passive(sentence):
    """Detect passive voice that could be active, excluding acceptable academic passives."""
    match = PASSIVE_PATTERN.search(sentence)
    if not match:
        return False

    # Check if "by" agent is present
    has_by_agent = match.group(4) is not None

    # Check if the passive construction is in the acceptable list
    passive_phrase = match.group(0).strip().lower()

    # If "by" agent is present, flag it regardless (unnecessary passive)
    # e.g., "was conducted BY the team" should be flagged as passive misuse
    if has_by_agent:
        return True

    # Without "by" agent, only flag if it's NOT in the acceptable list
    for acceptable in ACCEPTABLE_PASSIVE_CONTEXTS:
        if acceptable in passive_phrase or passive_phrase.startswith(acceptable):
            return False

    # Flag passives without "by" that aren't in the acceptable list
    return True


def _suggest_active_voice(sentence):
    """Suggest converting passive to active voice."""
    # This is a heuristic - full conversion requires NLP.
    # We flag the issue and provide a general suggestion.
    match = PASSIVE_PATTERN.search(sentence)
    if not match:
        return None

    passive_phrase = match.group(0).strip()
    verb = match.group(2)

    # Suggest replacing "was X by Y" → "Y Xed"
    # e.g., "was conducted by the team" → "the team conducted"
    by_match = re.search(r"\bby\b", passive_phrase)
    if by_match:
        after_by = sentence[match.end():].strip().split()[0] if match.end() < len(sentence) else ""
        # Provide suggestion template
        suggestion = (f"Consider active voice: identify the agent performing the action "
                      f"and make it the subject. E.g., rephrase '{passive_phrase}' "
                      f"to place the doer before the verb.")
        return suggestion
    return None


def _detect_weak_verb(sentence):
    """Detect weak verb + adjective patterns."""
    for pattern, _ in WEAK_VERB_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_stronger_verb(sentence):
    """Suggest stronger verb alternatives."""
    for pattern, suggestion_template in WEAK_VERB_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            return f"Consider a stronger verb instead of 'is'/'are'. E.g., use {suggestion_template}."
    return None


def _detect_vague_language(sentence):
    """Detect hedging words and vague nouns/adjectives."""
    for pattern in HEDGING_WORDS + VAGUE_NOUNS + VAGUE_ADJECTIVES:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_precise_language(sentence):
    """Suggest replacing vague language with precise terms."""
    findings = []
    for pattern in HEDGING_WORDS:
        m = re.search(pattern, sentence, re.IGNORECASE)
        if m:
            findings.append(f"'{m.group(1)}' → use precise quantifiers or omit")
            break
    for pattern in VAGUE_NOUNS:
        m = re.search(pattern, sentence, re.IGNORECASE)
        if m:
            findings.append(f"'{m.group(1)}' → use a more specific term")
            break
    for pattern in VAGUE_ADJECTIVES:
        m = re.search(pattern, sentence, re.IGNORECASE)
        if m:
            findings.append(f"'{m.group(1)}' → use a more precise descriptor")
            break
    if findings:
        return "Replace vague language: " + "; ".join(findings)
    return None


def _detect_redundancy(sentence):
    """Detect redundant/tautological phrases."""
    for pattern, _ in REDUNDANT_PHRASES:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_redundancy_fix(sentence):
    """Suggest removing redundant phrases."""
    result = sentence
    for pattern, replacement in REDUNDANT_PHRASES:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    if result != sentence:
        return result
    return None


def _detect_colloquialism(sentence):
    """Detect informal/conversational phrasing."""
    for pattern, _ in COLLOQUIAL_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def _suggest_formal_alternative(sentence):
    """Suggest formal alternatives to colloquial phrases."""
    for pattern, suggestion in COLLOQUIAL_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            m = re.search(pattern, sentence, re.IGNORECASE)
            return f"Replace '{m.group(0).strip()}' with a more formal alternative (e.g., {suggestion})"
    return None


def _detect_complex_sentence(sentence):
    """Detect overly complex sentences."""
    if is_overly_long(sentence):
        return True
    clause_count = count_clauses(sentence)
    return clause_count > MAX_CLAUSES


def _suggest_simpler_sentence(sentence):
    """Suggest simplifying complex sentences."""
    word_count = len(sentence.split())
    clause_count = count_clauses(sentence)
    suggestions = []
    if word_count > 40:
        suggestions.append(f"sentence is {word_count} words (aim for < 40)")
    if clause_count > 3:
        suggestions.append(f"sentence has ~{clause_count} clauses (aim for ≤ 3)")
    if suggestions:
        return "Consider breaking into shorter sentences: " + "; ".join(suggestions)
    return None


def _detect_weak_opener(sentence):
    """Detect weak sentence openers."""
    return has_weak_opener(sentence)


def _suggest_stronger_opener(sentence):
    """Suggest stronger sentence openers."""
    for pattern in WEAK_OPENERS:
        if re.match(pattern, sentence.strip()):
            opener = pattern.strip("^").replace("\\b", "").strip()
            return (f"Consider rewriting to avoid starting with '{opener}'. "
                    f"Place the real subject earlier in the sentence.")
    return None