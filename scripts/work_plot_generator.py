"""Conservative, original Italian plot synopses from corroborated plot relations.

This is deliberately not an LLM or free-form summary: only a specifically
labelled Wikipedia plot section and two independently stated character actions
permit a short original synopsis. Unknown or ambiguous text stays unpublished.
"""
from __future__ import annotations
import re

NAME = r"([A-ZÀ-Ü][a-zà-ÿ]{2,24}(?:['’][A-ZÀ-Ü]?[a-zà-ÿ]+)?)"
PLOT_HEADING = re.compile(r"==\s*(?:Trama|La trama|Argomento)\s*==|(?:^|\n)(?:Trama|La trama|Argomento)\s*\n", re.I)
NEXT_HEADING = re.compile(r"==\s*[^=]+\s*==|\n(?:Note|Bibliografia|Collegamenti esterni|Personaggi|Discografia|Accoglienza)\s*\n", re.I)
LOVE = re.compile(NAME + r"\s+(?:si innamora di|ama)\s+" + NAME + r"\b")
QUEST = re.compile(NAME + r"\s+(?:cerca di|tenta di)\s+(salvare|liberare|ritrovare|proteggere)\s+" + NAME + r"\b", re.I)
BETRAY = re.compile(NAME + r"\s+(uccide|tradisce|inganna|accusa|sposa)\s+" + NAME + r"\b", re.I)
GENERIC = re.compile(r"\b(?:opera|atto|scena|teatro|personaggi|trama|storia|prologo)\b", re.I)


def synopsis_from_wikipedia_plot(extract: str | None) -> str | None:
    """Return original, structured one-sentence prose or fail closed.

    Two DIFFERENT relations must appear within the Wikipedia plot section.
    No arbitrary excerpts, presumed settings, motives or invented endings.
    """
    if not isinstance(extract, str) or len(extract) > 12000:
        return None
    heading = PLOT_HEADING.search(extract)
    if not heading:
        return None
    remaining = extract[heading.end():]
    next_heading = NEXT_HEADING.search(remaining)
    plot = (remaining[:next_heading.start()] if next_heading else remaining)[:6500]
    # Ignore lines that only describe acts or editorial metadata.
    if len(plot) < 90:
        return None
    facts = []
    for regex, kind in ((LOVE, "love"), (QUEST, "quest"), (BETRAY, "betray")):
        for match in regex.finditer(plot):
            parts = match.groups()
            if any(GENERIC.fullmatch(p) for p in parts):
                continue
            if kind == "love" and parts[0] == parts[1]:
                continue
            if kind != "love" and parts[0] == parts[-1]:
                continue
            facts.append((match.start(), kind, parts))
    facts.sort()
    # Only coherent pairs concerning at least one shared named character.
    for i, (_, a, left) in enumerate(facts):
        for _, b, right in facts[i + 1:]:
            names_a = {left[0], left[-1]}
            names_b = {right[0], right[-1]}
            if not (names_a & names_b) or (a, left) == (b, right):
                continue
            def clause(kind, values):
                if kind == "love":
                    return f"{values[0]} prova amore per {values[1]}"
                if kind == "quest":
                    return f"{values[0]} tenta di {values[1].lower()} {values[2]}"
                verbs = {"uccide": "uccide", "tradisce": "tradisce", "inganna": "inganna", "accusa": "accusa", "sposa": "sposa"}
                return f"{values[0]} {verbs[values[1].lower()]} {values[2]}"
            result = "Nella vicenda, " + clause(a, left) + "; " + clause(b, right) + "."
            if 45 <= len(result) <= 220 and result.lower() not in plot.lower():
                return result
    return None
