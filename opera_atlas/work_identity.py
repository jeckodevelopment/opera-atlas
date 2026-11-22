"""Reviewed multilingual work-title aliases, keyed by the verified composer.

The registry stays the single authority for permanent work IDs. Never
fuzzy-match a title or infer composer from a translated title alone.
"""
from __future__ import annotations
import re
import unicodedata

def _key(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("work title and composer are required")
    return unicodedata.normalize("NFKC", text).casefold().strip().replace("’", "'")

# Only historically verified equivalences with composer disambiguation.
# New languages/aliases may be added after editorial review of the work.
ALIASES = {
    ("don carlo", "giuseppe verdi"): "Don Carlos",
    ("die zauberflote", "wolfgang amadeus mozart"): "Die Zauberflöte",
    ("il flauto magico", "wolfgang amadeus mozart"): "Die Zauberflöte",
    ("the magic flute", "wolfgang amadeus mozart"): "Die Zauberflöte",
    ("tristano e isotta", "richard wagner"): "Tristan und Isolde",
    ("tristan and isolde", "richard wagner"): "Tristan und Isolde",
    ("sansone e dalila", "camille saint-saëns"): "Samson et Dalila",
    ("samson and delilah", "camille saint-saëns"): "Samson et Dalila",
    ("i pescatori di perle", "georges bizet"): "Les Pêcheurs de perles",
    ("the pearl fishers", "georges bizet"): "Les Pêcheurs de perles",
    ("les pecheurs de perles", "georges bizet"): "Les Pêcheurs de perles",
    ("i racconti di hoffmann", "jacques offenbach"): "Les contes d'Hoffmann",
    ("the tales of hoffmann", "jacques offenbach"): "Les contes d'Hoffmann",
    ("hansel e gretel", "engelbert humperdinck"): "Hänsel und Gretel",
    ("hansel and gretel", "engelbert humperdinck"): "Hänsel und Gretel",
    ("haensel und gretel", "engelbert humperdinck"): "Hänsel und Gretel",
    ("don chisciotte", "jules massenet"): "Don Quichotte",
    ("ifigenia in tauride", "christoph willibald gluck"): "Iphigénie en Tauride",
    ("didone ed enea", "henry purcell"): "Dido and Æneas",
    ("dido and aeneas", "henry purcell"): "Dido and Æneas",
    ("die fledermaus", "johann strauss"): "Il pipistrello",
    ("the bat", "johann strauss"): "Il pipistrello",
    ("morte a venezia", "benjamin britten"): "Death in Venice",
    ("cinderella", "gioachino rossini"): "La Cenerentola",
    ("la cenerentola, ossia la bontà in trionfo", "gioachino rossini"): "La Cenerentola",
    ("the barber of seville", "gioachino rossini"): "Il barbiere di Siviglia",
    ("the marriage of figaro", "wolfgang amadeus mozart"): "Le nozze di Figaro",
    ("la carriera di un libertino", "igor' stravinskij"): "The Rake's Progress",
    ("il ritorno d'ulisse in patria", "claudio monteverdi"): "Il ritorno di Ulisse in patria",
    ("the return of ulysses to his homeland", "claudio monteverdi"): "Il ritorno di Ulisse in patria",
    ("eugene onegin", "pëtr il'ič čajkovskij"): "Evgenij Onegin",
    ("yevgeny onegin", "pëtr il'ič čajkovskij"): "Evgenij Onegin",
}

def canonical_title(title: str, composer: str) -> str:
    """Map an explicitly reviewed translation to the canonical title.

    No guesses for homonyms, different composers, or misspellings.
    """
    title_key, composer_key = _key(title), _key(composer)
    mapped = ALIASES.get((title_key, composer_key))
    return mapped if mapped is not None else title

def _verified_composer_credit(credit: str, canonical: str) -> bool:
    """Accept only exact credits or narrowly defined trailing catalogue metadata.

    Do not remove arbitrary words: those may identify another composer or
    represent an incorrectly parsed source. The canonical composer is taken
    from the registry, never inferred from the performance title.
    """
    if _key(credit) == _key(canonical):
        return True
    prefix = canonical + " "
    if not credit.casefold().startswith(prefix.casefold()):
        return False
    suffix = credit[len(prefix):].strip()
    return bool(re.fullmatch(r"(?:Opera|Tragedia|Melodramma|\(\d{4}[–-]\d{4}\))", suffix, re.I))


def resolve_work(registry: dict, title: str, composer: str) -> dict | None:
    """Require one canonical title + verified composer, including safe credit metadata."""
    _key(title)
    _key(composer)
    matches = [
        record for record in list(registry.get("works", {}).values()) + list(registry.get("reserved_works", {}).values())
        if _verified_composer_credit(composer, record["composer"])
        and _key(record["title"]) == _key(canonical_title(title, record["composer"]))
    ]
    return matches[0] if len(matches) == 1 else None
