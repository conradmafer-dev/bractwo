"""Small, local profanity filter for public comments in Polish and English.

This is a curated vocabulary, not a guarantee of detecting every insult or
obfuscation. Match complete words and explicit inflections: substring filters
would reject ordinary words such as ``słuchaj`` or ``Scunthorpe``.
"""
from __future__ import annotations

from functools import lru_cache
import re
import unicodedata


# Explicit endings keep morphology reviewable without matching arbitrary words
# that happen to contain one of these stems. Accents are folded before matching.
_POLISH_PATTERNS = (
    r"kurw(?:a|y|ie|e|o|om|ami|ach|ski|ska|skie|sko|stwo|ica|icy|ice|iarz|iarza|iarze|iarzem|iarzu)",
    r"kurwiszon(?:a|y|em|ie|om|ami|ach)?",
    r"skurwiel(?:a|e|em|owi|om|ami|ach|u|i)?",
    r"skurwysyn(?:a|y|em|ie|owi|om|ami|ach|ski|ska|skie|stwo)?",
    r"(?:w|wy|za)kurw(?:ic|ia|iam|iasz|iaja|iaj|iajcie|iony|iona|ione|ienie)",
    r"(?:chuj|huj)(?:a|u|e|em|owi|om|ami|ach|owy|owa|owe|owo|owych|owym|owymi|nia|nie|ni|ek|ki|kow)?",
    r"dup(?:a|y|ie|e|o|om|ami|ach|ek|ka|ki|kiem|kow|kom|kami|kach|sko|skow)",
    r"cip(?:a|y|ie|e|o|om|ami|ach|ka|ki|ke|ko|kom|kami|kach)",
    r"dziwk(?:a|i|e|o|om|ami|ach)",
    r"pizd(?:a|y|zie|e|o|om|ami|ach|ec)",
    r"gown(?:o|a|u|em|ie|iany|iana|iane|ianego|ianej|ianych|iarz|iarza|iarze)",
    r"(?:do|na|od|po|prze|przy|roz|wy|za|z)?jeb(?:ac|iac|ie|ia|iesz|iemy|iecie|cie|nij|nijcie|niety|nieta|niete|al|ala|ali|aly|alem|alam|ales|alas|any|ana|ane|ani|anego|anej|anych|anie|ania|aniu|aniem|isty|ista|iste|iscie|istego|istej|istych)",
    r"(?:po|z)jeb(?:a|em|y|ie|ami|ach|ow)?",
    r"(?:do|ja|na|od|po|prze|przy|roz|s|wy|za)?pierdol(?:e|isz|i|imy|icie|cie|nij|nijcie|nie|niesz|niety|nieta|niete|a|ic|il|ila|ili|ily|ilem|ilam|iles|ilas|ony|ona|one|eni|onego|onej|onych|enie|enia|eniu|eniem)?",
    r"(?:do|na|od|po|prze|przy|roz|s|wy|za)?pierdal(?:ac|aj|ajcie|am|asz|a|amy|acie|aja|al|ala|ali|aly|alem|alam|ales|alas|anie|ania|aniu)",
)
_ENGLISH_PATTERNS = (
    r"fuck(?:s|ed|er|ers|ing|off|head|heads|wit|wits)?",
    r"motherfuck(?:er|ers|ing)",
    r"(?:bull)?shit(?:s|ty|tier|tiest|ting|head|heads|hole|holes|show)?",
    r"bitch(?:es|ing|y)?",
    r"cunt(?:s)?",
    r"dick(?:s|head|heads)?",
    r"ass(?:es|hole|holes)?",
    r"piss(?:ed|ing|off)?",
    r"bastard(?:s)?",
    r"whore(?:s)?",
    r"slut(?:s|ty)?",
)


def _allow_repeated_letters(pattern: str) -> str:
    # Patterns above use literal letters and groups, not character classes.
    # Keep doubled letters significant: "piss" must not match Polish "PiS".
    return re.sub(r"[a-z]", lambda match: "(?:" + match[0] + "{1,2})", pattern)


_WORD = re.compile("(?:" + "|".join(
    _allow_repeated_letters(pattern)
    for pattern in _POLISH_PATTERNS + _ENGLISH_PATTERNS
) + ")")
_TOKENS = re.compile(r"(?:[^\W_]|[@$*])+")
_ASCII_TOKEN = re.compile(r"[a-z*]+")
_REPEATS = re.compile(r"([a-z])\1{2,}")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a",
                       "5": "s", "7": "t", "8": "b", "@": "a", "$": "s"})
_MASKED_WORDS = (
    "kurwa", "kurwy", "kurwie", "chuj", "chuja", "chuje", "chujowy",
    "jebac", "jebany", "jebana", "jebane", "pierdolic", "pierdolony",
    "pierdolona", "pierdolone", "spierdalaj", "wypierdalaj", "gowno",
    "dupa", "dupie", "pizda", "fuck", "fucker", "fucking", "shit",
    "bitch", "cunt", "asshole", "dick",
)
_MASKED_BY_INITIAL = {initial: tuple(word for word in _MASKED_WORDS if word[0] == initial)
                      for initial in {word[0] for word in _MASKED_WORDS}}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("ł", "l")
    text = "".join(char for char in unicodedata.normalize("NFKD", text)
                   if not unicodedata.category(char).startswith("M")
                   and unicodedata.category(char) != "Cf")
    # A bang inside a word is common leetspeak; sentence-ending bangs remain
    # punctuation so "kurwa!" is still checked as the complete word.
    text = re.sub(r"(?<=[a-z0-9])!+(?=[a-z0-9])", "i", text)
    return text.translate(_LEET)


def _masked_match(parts: list[str], word: str) -> bool:
    """Match each censorship run to 1–4 letters without compiling user input."""
    positions = {len(parts[0])}
    for part in parts[1:]:
        positions = {position + missing + len(part)
                     for position in positions for missing in range(1, 5)
                     if word.startswith(part, position + missing)}
        if not positions:
            return False
    return len(word) in positions


@lru_cache(maxsize=4096)
def _matches(candidate: str) -> bool:
    candidate = _REPEATS.sub(r"\1\1", candidate).strip("*")
    if _WORD.fullmatch(candidate.replace("*", "")):
        return True
    # Support recognisable censorship (k**wa, ch*j, f**k) without treating
    # arbitrary unknown letters as wildcards throughout ordinary prose.
    masked_words = _MASKED_BY_INITIAL.get(candidate[:1], ())
    if masked_words and "*" in candidate and sum(char.isalpha() for char in candidate) >= 2:
        parts = re.split(r"\*+", candidate)
        gaps = len(parts) - 1
        visible = sum(map(len, parts))
        # Most punctuation in ordinary text cannot hide any word here. Cheap
        # fixed checks also bound work for deliberately varied mask strings.
        return any(_masked_match(parts, word) for word in masked_words
                   if visible + gaps <= len(word) <= visible + 4 * gaps
                   and word.startswith(parts[0]) and word.endswith(parts[-1]))
    return False


def contains_profanity(text: str) -> bool:
    """Return whether text contains a recognised profane word or common evasion.

    Callers validate type and length separately. Short sequences of complete
    tokens are joined to catch inserted punctuation/spaces, without looking
    inside longer words. Candidate caching is bounded; there are no network
    calls, persistent state or optional dependencies.
    """
    # The folded vocabulary is ASCII. Other scripts/digits form boundaries,
    # so compatibility characters that expand into long non-Latin sequences
    # cannot multiply the candidate scan.
    tokens = [_REPEATS.sub(r"\1\1", token) if _ASCII_TOKEN.fullmatch(token) else ""
              for token in _TOKENS.findall(_normalize(text))]
    for index in range(len(tokens)):
        if not tokens[index]:
            continue
        candidate = ""
        for token in tokens[index:index + 12]:
            if not token:
                break
            candidate += token
            # Bound separator handling; a long unrelated word is a boundary.
            if len(candidate) > 64:
                break
            if _matches(candidate):
                return True
    return False
