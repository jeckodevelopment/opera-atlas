"""Read-only 2026 residual audit: check canonical recite before proposing additions.

Never classify a same-day performance as missing without verifying its work,
venue and published calendar. Differences in clock are conflicts, not additions.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit_2026_retrospective_reconciliation import norm

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "public/diagnostics/atlas-2026-editorial-triage.json"
CATALOG = ROOT / "data/verified-launch-catalog.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-residual-catalog-check.json"

# These entries are aliases / attributive composer headings *on the source*,
# not permission to merge different opera titles by similarity.
TITLE_PREFIXES = (
    ("giuseppe verdi", "macbeth"),
    ("richard wagner", "der fliegende hollander"),
    ("salvatore passantino", "l esecuzione"),
    ("daniele furlati", "i salvatori della mezzanotte"),
)
# Explicit official same-host source for three performances; no heuristic
# decisions should be applied to unrelated future titles or dates.
SOURCE_CITY = {"modena-teatro-opera-2026-27":"modena",
               "piacenza-opera-2026-27":"piacenza",
               "bellini-catania-opera-2026-27":"catania",
               "bologna-comunale-opera-2027":"bologna",
               "maggio-fiorentino-calendar-2027":"firenze"}

OFFICIAL_NONOPERA = {
    ("https://www.tcbo.it/evento/speciale/opera-guccini-2026/", "Opera Guccini"):
    {"days":["2026-10-29","2026-10-30","2026-10-31"],
     "reason":"The Teatro Comunale di Bologna describes the event as a concert-show of Guccini songs, not a staged opera.",
     "official_detail_url":"https://www.tcbo.it/evento/speciale/opera-guccini-2026/"},
}


# Frozen 2026 first-party detail-page verification. Keys are restricted to an
# existing source, canonical title, exact observed day and physical venue.
# These *diagnostic* findings do not modify editorial decisions or catalogue.
OFFICIAL_GENRE_EVIDENCE = (
    {
        "source_key":"bellini-catania-opera-2026-27",
        "title":"La bella addormentata",
        "days":tuple(f"2026-12-{d:02d}" for d in range(1,7)),
        "venue":"Teatro Metropolitan.",
        "genre":"ballet",
        "official_detail_url":"https://www.teatromassimobellini.it/eventi/la-bella-addormentata-5/",
        "official_genre_url":"https://www.teatromassimobellini.it/al-via-i-lavori-di-riqualificazione-e-adeguamento-alla-sicurezza-del-monumentale-teatro-massimo-v-bellini/",
        "reason":"The theatre explicitly identifies the 1-6 December performances as a ballet in three acts, not an opera.",
    },
    {
        "source_key":"bologna-comunale-opera-2027",
        "title":"Pierino e il lupo",
        "days":("2026-10-10","2026-10-17","2026-11-21","2026-11-28","2026-12-12"),
        "venue":None,
        "genre":"children_concert",
        "official_detail_url":"https://www.tcbo.it/evento/accademia/pierino-e-il-lupo-2026/",
        "official_genre_url":"https://www.tcbo.it/evento/accademia/pierino-e-il-lupo-2026/",
        "reason":"The official programme categorizes all five dated performances as a narrated concert for children aged three to six.",
    },
    {
        "source_key":"modena-teatro-opera-2026-27", "title":"I love you, Schubert! / Play Bach – Balletto Teatro di Torino",
        "days":["2026-07-24"], "venue":None,
        "genre":"dance", "official_detail_url":"https://www.teatrocomunalemodena.it/spettacolo/play-bach-i-love-you-schubert-balletto-di-torino/",
        "official_genre_url":"https://www.teatrocomunalemodena.it/spettacolo/play-bach-i-love-you-schubert-balletto-di-torino/",
        "reason":"Teatro di Modena: Danza, Balletto Teatro di Torino; event 24 July.",
    },
    {
        "source_key":"modena-teatro-opera-2026-27", "title":"I bislacchi – Artemis Danza",
        "days":["2026-07-26"], "venue":"Parco dei Castagni",
        "genre":"dance", "official_detail_url":"https://www.teatrocomunalemodena.it/spettacolo/i-bislacchi-artemis-danza/",
        "official_genre_url":"https://www.teatrocomunalemodena.it/spettacolo/i-bislacchi-artemis-danza/",
        "reason":"Official Modena event classifies Artemis Danza as dance, 26 July.",
    },
    {
        "source_key":"modena-teatro-opera-2026-27", "title":"Compagnia Anželika Cholina Dance Theatre – Anna Karenina",
        "days":["2026-11-06"], "venue":"Teatro Comunale Pavarotti-Freni",
        "genre":"dance", "official_detail_url":"https://www.teatrocomunalemodena.it/spettacolo/compagnia-anzelika-cholina-dance-theatre-anna-karenina/",
        "official_genre_url":"https://www.teatrocomunalemodena.it/spettacolo/compagnia-anzelika-cholina-dance-theatre-anna-karenina/",
        "reason":"Official Modena page labels production Danza, 6 November.",
    },
    {
        "source_key":"modena-teatro-opera-2026-27", "title":"Serbian National Theatre – Giselle",
        "days":["2026-12-01"], "venue":"Teatro Comunale Pavarotti-Freni",
        "genre":"ballet", "official_detail_url":"https://www.teatrocomunalemodena.it/spettacolo/serbian-national-theatre-giselle/",
        "official_genre_url":"https://www.teatrocomunalemodena.it/spettacolo/serbian-national-theatre-giselle/",
        "reason":"Official Modena event identifies Giselle as ballet on 1 December.",
    },
    {
        "source_key":"modena-teatro-opera-2026-27", "title":"Compagnia Artemis Danza – Verdi/Shakespeare: Trilogia della brama",
        "days":["2026-12-16"], "venue":"Teatro Comunale Pavarotti-Freni",
        "genre":"dance", "official_detail_url":"https://www.teatrocomunalemodena.it/spettacolo/compagnia-artemis-danza-verdi-shakespeare-trilogia-della-brama/",
        "official_genre_url":"https://www.teatrocomunalemodena.it/spettacolo/compagnia-artemis-danza-verdi-shakespeare-trilogia-della-brama/",
        "reason":"Official Modena page classifies Verdi/Shakespeare as Danza, not staged opera.",
    },
    {
        "source_key":"bologna-comunale-opera-2027", "title":"The Lion King Live in Concert",
        "days":["2026-12-18","2026-12-19","2026-12-20"], "venue":"Teatro EuropAuditorium",
        "genre":"film_with_live_orchestra", "official_detail_url":"https://www.tcbo.it/en/evento/speciale/the-lion-king-live-in-concert-2026/",
        "official_genre_url":"https://www.tcbo.it/en/evento/speciale/the-lion-king-live-in-concert-2026/",
        "reason":"Official TCBO categorizes all three dates as film projection with live orchestra.",
    },
    {
        "source_key":"piacenza-opera-2026-27", "title":"Siberia | prova aperta alle scuole",
        "days":["2026-12-14"], "venue":"Teatro Municipale",
        "genre":"school_only_rehearsal", "official_detail_url":"https://teatripiacenza.it/event/siberia/",
        "official_genre_url":"https://teatripiacenza.it/event/siberia/",
        "reason":"Official Piacenza event restricts 14 December rehearsal to pupils and accompanying teachers.",
    },
    {
        "source_key":"piacenza-opera-2026-27", "title":"Siberia | anteprima #Siberia18",
        "days":["2026-12-16"], "venue":"Teatro Municipale",
        "genre":"restricted_age_preview", "official_detail_url":"https://teatripiacenza.it/event/siberia/",
        "official_genre_url":"https://teatripiacenza.it/event/siberia/",
        "reason":"Official Piacenza production reserves 16 December preview to young people turning 18 in 2026-27.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Passione e tormento",
        "days": ["2026-11-08"], "venue": "Accademia Filarmonica",
        "genre": "concert", "official_detail_url": "https://www.tcbo.it/evento/accademia/domenica-in-musica-ii-appuntamento-2026/",
        "official_genre_url": "https://www.tcbo.it/evento/accademia/domenica-in-musica-ii-appuntamento-2026/",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Follie, intrighi e virtuosismo",
        "days": ["2026-11-22"], "venue": "Museo Internazionale e Biblioteca della Musica",
        "genre": "concert", "official_detail_url": "https://www.tcbo.it/evento/accademia/domenica-in-musica-iii-appuntamento-2026/",
        "official_genre_url": "https://www.tcbo.it/evento/accademia/domenica-in-musica-iii-appuntamento-2026/",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Concerto di Gala del corso rossiniano",
        "days": ["2026-11-26"], "venue": "Teatro Comunale di San Giovanni in Persiceto",
        "genre": "concert", "official_detail_url": "https://www.tcbo.it/en/evento/accademia/concerto-di-gala-del-corso-rossiniano-2026/",
        "official_genre_url": "https://www.tcbo.it/en/evento/accademia/concerto-di-gala-del-corso-rossiniano-2026/",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Viaggio nell’Elisir d’amore",
        "days": ["2026-12-13"], "venue": "Circolo Culturale Lirico Bolognese",
        "genre": "concert", "official_detail_url": "https://www.tcbo.it/en/evento/accademia/domenica-in-musica-iv-appuntamento-2026/",
        "official_genre_url": "https://www.tcbo.it/en/evento/accademia/domenica-in-musica-iv-appuntamento-2026/",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "maggio-fiorentino-calendar-2027", "title": "Verdi Game",
        "days": ["2026-11-26"], "venue": "Istituto Baccio da Montelupo - Montelupo Fiorentino",
        "genre": "interactive_educational_theatre", "official_detail_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "official_genre_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "maggio-fiorentino-calendar-2027", "title": "Verdi Game",
        "days": ["2026-12-02"], "venue": "Istituto Comprensivo \"Anna Maria Luisa De' Medici\" - Calenzano",
        "genre": "interactive_educational_theatre", "official_detail_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "official_genre_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "maggio-fiorentino-calendar-2027", "title": "Verdi Game",
        "days": ["2026-12-09"], "venue": "Teatrodante \"Carlo Monni\" - Campi Bisenzio",
        "genre": "interactive_educational_theatre", "official_detail_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "official_genre_url": "https://www.maggiofiorentino.com/events/verdi-game-2026",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "Dido and Aeneas (Generale riservata alle Scuole)",
        "days": ["2026-10-21"], "venue": None,
        "genre": "school_only_rehearsal", "official_detail_url": "https://teatrodipisa.it/calendario/categoria/opera/elenco/?eventDisplay=past",
        "official_genre_url": "https://teatrodipisa.it/calendario/categoria/opera/elenco/?eventDisplay=past",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "L’occasione fa il ladro (Generale riservata alle Scuole)",
        "days": ["2026-12-02"], "venue": None,
        "genre": "school_only_rehearsal", "official_detail_url": "https://teatrodipisa.it/calendario/categoria/opera/elenco/?eventDisplay=past",
        "official_genre_url": "https://teatrodipisa.it/calendario/categoria/opera/elenco/?eventDisplay=past",
        "reason": "Official first-party calendar classifies this as a concert, educational theatre or restricted school rehearsal rather than an ordinary public opera performance.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Il cambiamento era incessante",
        "days": ["2026-09-16"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/il-cambiamento-era-incessante/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/il-cambiamento-era-incessante/",
        "reason": "Official detail describes a concert of selected Handel arias, not a full opera.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "La costanza trionfante",
        "days": ["2026-09-25"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "opera_semiscenic_reconstruction", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/la-costanza-trionfante/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/la-costanza-trionfante/",
        "reason": "Vivaldi RV 706-A: only surviving music performed semi-staged with spoken narration of lost sections; requires editorial scope review.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Kammermusik n. 1",
        "days": ["2026-09-26"], "venue": "Galleria Estense, Sala dei Veneti",
        "genre": "chamber_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/kammermusik-n-1-2/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/kammermusik-n-1-2/",
        "reason": "Festival detail explicitly calls this a masterclass concert.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Voci inaudite",
        "days": ["2026-09-26"], "venue": "Chiesa di San Carlo",
        "genre": "contemporary_vocal_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/voci-inaudite/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/voci-inaudite/",
        "reason": "First-party page describes two-part vocal concert, not an opera staging.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Kattivissimi and friends… all’Opera",
        "days": ["2026-09-27"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "educational_opera_encounter", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/kattivissimi-and-friends-allopera/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/kattivissimi-and-friends-allopera/",
        "reason": "Official detail describes a children and families illustrated introduction to opera characters.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Letteralmente Verdi",
        "days": ["2026-09-27"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "narrated_music_event", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/letteralmente-verdi/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/letteralmente-verdi/",
        "reason": "First-party detail describes musical narration about Verdi and Il trovatore rather than staged Il trovatore.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Ma l’amor mio non muore!",
        "days": ["2026-09-30"], "venue": "Sala Truffaut",
        "genre": "silent_film_live_score", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/ma-lamor-mio-non-muore/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/ma-lamor-mio-non-muore/",
        "reason": "Official festival detail: screening of restored 1913 silent film with newly composed live music.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Viva Verdi",
        "days": ["2026-10-02"], "venue": "Teatro del Popolo, Concordia sulla Secchia (MO)",
        "genre": "dance", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/viva-verdi/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/viva-verdi/",
        "reason": "Balletto di Milano performs choreography to Verdi ballet music, not staged opera.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Kammermusik n. 2",
        "days": ["2026-10-03"], "venue": "Palazzo Ducale di Sassuolo",
        "genre": "chamber_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/kammermusik-n-2-2/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/kammermusik-n-2-2/",
        "reason": "Official festival programme describes a masterclass chamber concert.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Concerto di Gala",
        "days": ["2026-10-04"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "gala_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/concerto-di-gala-2/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/concerto-di-gala-2/",
        "reason": "First-party description: gala concert featuring Anna Pirozzi celebrating Verdi.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "A casa Bononcini",
        "days": ["2026-10-09"], "venue": "Chiesa di San Carlo",
        "genre": "baroque_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/a-casa-bononcini/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/a-casa-bononcini/",
        "reason": "Official page explicitly describes a baroque music concert.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Messa da Requiem",
        "days": ["2026-10-10"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "sacred_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/messa-da-requiem/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/messa-da-requiem/",
        "reason": "Verdi Messa da Requiem is a concert performance of sacred work, not a theatrical opera staging.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Dalla Boemia al Ducato di Modena",
        "days": ["2026-10-11"], "venue": "Temple Theater /Teatro A. Rompianesi, Sassuolo",
        "genre": "chamber_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/dalla-boemia-al-ducato-di-modena-3/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/dalla-boemia-al-ducato-di-modena-3/",
        "reason": "Official programme for flautist and pianist, not opera staging.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Mamma: tributo a Luciano Pavarotti e Henry Mancini",
        "days": ["2026-10-12"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "tribute_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/spettacolo-a-cura-della-fondazione-luciano-pavarotti/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/spettacolo-a-cura-della-fondazione-luciano-pavarotti/",
        "reason": "Pavarotti and Mancini tribute musical programme, not a staged opera.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Filarmonie Future",
        "days": ["2026-10-13"], "venue": "Teatro Comunale di Carpi",
        "genre": "opera_gala_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/filarmonie-future-2/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/filarmonie-future-2/",
        "reason": "Official event describes an orchestral concert of excerpts from Mozart, Rossini, Verdi and Puccini.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "La preghiera nell’opera lirica",
        "days": ["2026-10-17"], "venue": "Chiesa di Sant'Agostino",
        "genre": "choral_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/la-preghiera-nellopera-lirica/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/la-preghiera-nellopera-lirica/",
        "reason": "Official detail describes a choral concert of operatic prayer excerpts.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Le maschere allo specchio",
        "days": ["2026-10-17"], "venue": "Ridotto del Teatro",
        "genre": "contemporary_chamber_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/le-maschere-allo-specchio/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/le-maschere-allo-specchio/",
        "reason": "Official programme presents selected contemporary chamber and vocal pieces, not a complete opera.",
    },
    {
        "source_key": "modena-teatro-opera-2026-27", "title": "Caterina Barbieri e Fontanamix ensemble",
        "days": ["2026-11-12"], "venue": "Teatro Comunale Pavarotti-Freni",
        "genre": "cancelled_concert", "official_detail_url": "https://www.teatrocomunalemodena.it/spettacolo/caterina-barbieri-e-fontanamix-ensemble/",
        "official_genre_url": "https://www.teatrocomunalemodena.it/spettacolo/caterina-barbieri-e-fontanamix-ensemble/",
        "reason": "Official venue explicitly states that this concert was cancelled and tickets are refunded.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "¡QUÉ VIVA ESPAÑA",
        "days": ["2026-10-29"], "venue": "Teatro Metropolitan.",
        "genre": "symphonic_concert", "official_detail_url": "https://www.teatromassimobellini.it/eventi/que-viva-espana/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/que-viva-espana/",
        "reason": "Official event labeled Concerti and Concerto Sinfonico.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "¡QUÉ VIVA ESPAÑA",
        "days": ["2026-10-31"], "venue": "Teatro Metropolitan.",
        "genre": "symphonic_concert", "official_detail_url": "https://www.teatromassimobellini.it/eventi/que-viva-espana/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/que-viva-espana/",
        "reason": "Second dated performance of the same officially categorized symphonic concert.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "Il Natale del Redentore",
        "days": ["2026-11-03"], "venue": "Cattedrale Maria SS Annunziata Acireale",
        "genre": "concert", "official_detail_url": "https://www.teatromassimobellini.it/eventi/il-natale-del-redentore/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/il-natale-del-redentore/",
        "reason": "Official event category Concerti, in the Cathedral of Acireale.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "Aimez – vous Brahms?",
        "days": ["2026-11-07"], "venue": "Teatro Metropolitan.",
        "genre": "concert", "official_detail_url": "https://www.teatromassimobellini.it/eventi/aimez-vous-brahms/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/aimez-vous-brahms/",
        "reason": "First-party event category Concerti.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "Aimez – vous Brahms?",
        "days": ["2026-11-08"], "venue": "Teatro Metropolitan.",
        "genre": "concert", "official_detail_url": "https://www.teatromassimobellini.it/eventi/aimez-vous-brahms/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/aimez-vous-brahms/",
        "reason": "Second performance of an official concert event.",
    },
    {
        "source_key": "bellini-catania-opera-2026-27", "title": "RECITAL House of Puccini",
        "days": ["2026-11-28"], "venue": "Teatro Metropolitan.",
        "genre": "recital", "official_detail_url": "https://www.teatromassimobellini.it/eventi/recital-house-of-puccini/",
        "official_genre_url": "https://www.teatromassimobellini.it/eventi/recital-house-of-puccini/",
        "reason": "Official event category Recital, not a staged Puccini opera.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Studenti all’opera! – Il flauto magico",
        "days": ["2026-12-04"], "venue": "Teatro Auditorium Manzoni",
        "genre": "educational_semi_staged_opera", "official_detail_url": "https://www.tcbo.it/en/evento/accademia/studenti-allopera-il-flauto-magico-2026/",
        "official_genre_url": "https://www.tcbo.it/en/evento/accademia/studenti-allopera-il-flauto-magico-2026/",
        "reason": "Official TCBO detail: 90-minute semi-staged Mozart opera with academy singers; editorial review needed, not a concert-only exclusion.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Angius, Grazia",
        "days": ["2026-12-11"], "venue": "Teatro Auditorium Manzoni",
        "genre": "symphonic_concert", "official_detail_url": "https://www.tcbo.it/evento/concerto/angius-grazia-2026/",
        "official_genre_url": "https://www.tcbo.it/evento/concerto/angius-grazia-2026/",
        "reason": "TCBO classifies it under Concerti / Stagione Sinfonica.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Sauer",
        "days": ["2026-12-13"], "venue": "Teatro Auditorium Manzoni",
        "genre": "symphonic_concert", "official_detail_url": "https://www.tcbo.it/en/evento/concerto/sauer-2026/",
        "official_genre_url": "https://www.tcbo.it/en/evento/concerto/sauer-2026/",
        "reason": "TCBO official event under concerto.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Concerto di Natale",
        "days": ["2026-12-20"], "venue": "Teatro Auditorium Manzoni",
        "genre": "concert", "official_detail_url": "https://www.tcbo.it/en/evento/accademia/domenica-in-musica-concerto-di-natale-2026/",
        "official_genre_url": "https://www.tcbo.it/en/evento/accademia/domenica-in-musica-concerto-di-natale-2026/",
        "reason": "Official Domenica in Musica Christmas concert, not a staged opera.",
    },
    {
        "source_key": "bologna-comunale-opera-2027", "title": "Stenz",
        "days": ["2026-12-31"], "venue": "Teatro Auditorium Manzoni",
        "genre": "symphonic_concert", "official_detail_url": "https://www.tcbo.it/evento/concerto/stenz-2026/",
        "official_genre_url": "https://www.tcbo.it/evento/concerto/stenz-2026/",
        "reason": "Official TCBO symphonic concert: Panfili and Beethoven Symphony No. 9.",
    },
    {
        "source_key": "piacenza-opera-2026-27", "title": "Prima di andare in Scena | Siberia",
        "days": ["2026-12-13"], "venue": "Ridotto del Teatro Municipale",
        "genre": "pre_opera_public_talk", "official_detail_url": "https://teatripiacenza.it/event/prima-di-andare-in-scena-26-27/",
        "official_genre_url": "https://teatripiacenza.it/event/prima-di-andare-in-scena-26-27/",
        "reason": "Official event is an introductory pre-opera talk and listening guide, not a performance of Siberia.",
    },
    {
        "source_key": "piacenza-opera-2026-27", "title": "Siberia | #AperiOpera",
        "days": ["2026-12-15"], "venue": "Foyer del Teatro Municipale",
        "genre": "pre_opera_public_talk", "official_detail_url": "https://teatripiacenza.it/event/aperiopera-26-27/",
        "official_genre_url": "https://teatripiacenza.it/event/aperiopera-26-27/",
        "reason": "Official AperiOpera event with students discussing Siberia; 18 and 20 Dec are separate general-public operatic performances.",
    },
    {
        "source_key": "pisa-verdi-opera-2026-27", "title": "L’occasione fa il ladro (Generale riservata alle Scuole)",
        "days": ["2026-12-02"], "venue": None,
        "genre": "school_only_rehearsal", "official_detail_url": "https://teatrodipisa.it/calendario/",
        "official_genre_url": "https://teatrodipisa.it/calendario/",
        "reason": "Official Pisa programme explicitly marks 2 December as a school-only dress rehearsal, distinct from public 4 and 6 December shows.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "C’era una volta un re",
        "days": ["2026-10-31"], "venue": None,
        "genre": "musical_reading", "official_detail_url": "https://teatrodipisa.it/spettacolo/cera-una-volta-un-re-omaggio-a-carlo-collodi-per-i-200-anni-dalla-nascita/",
        "official_genre_url": "https://teatrodipisa.it/spettacolo/cera-una-volta-un-re-omaggio-a-carlo-collodi-per-i-200-anni-dalla-nascita/",
        "reason": "Official Pisa programme categorizes this Sergio Rubini event as a musical reading for Collodi bicentenary.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "Pimpa. Il musical a pois",
        "days": ["2026-11-07"], "venue": None,
        "genre": "children_musical", "official_detail_url": "https://teatrodipisa.it/spettacolo/pimpa-il-musical-a-pois/",
        "official_genre_url": "https://teatrodipisa.it/spettacolo/pimpa-il-musical-a-pois/",
        "reason": "First-party Pisa detail identifies a musical for families, not operatic performance.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "Prima del temporale",
        "days": ["2026-11-14"], "venue": None,
        "genre": "prose_theatre", "official_detail_url": "https://teatrodipisa.it/spettacolo/prima-del-temporale/",
        "official_genre_url": "https://teatrodipisa.it/spettacolo/prima-del-temporale/",
        "reason": "Official Pisa event is categorized Prosa.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "Prima del temporale",
        "days": ["2026-11-15"], "venue": None,
        "genre": "prose_theatre", "official_detail_url": "https://teatrodipisa.it/spettacolo/prima-del-temporale/",
        "official_genre_url": "https://teatrodipisa.it/spettacolo/prima-del-temporale/",
        "reason": "Second of two Prosa performances, not opera.",
    },
    {
        "source_key": "pisa-future-calendar", "title": "Dido and Aeneas | Guida all’ascolto con Enrico Girardi",
        "days": ["2026-10-22"], "venue": None,
        "genre": "opera_introduction_talk", "official_detail_url": "https://teatrodipisa.it/en/calendario/dido-and-aeneas-guida-allascolto-con-enrico-girardi/",
        "official_genre_url": "https://teatrodipisa.it/en/calendario/dido-and-aeneas-guida-allascolto-con-enrico-girardi/",
        "reason": "Official Pisa listening guide precedes public opera dates 23/25 October and is not a recita.",
    },
)


def official_genre_evidence(group):
    """Only explicit first-party day/work/venue evidence; never title-only."""
    from urllib.parse import urlsplit
    for evidence in OFFICIAL_GENRE_EVIDENCE:
        if (group.get("source_key") != evidence["source_key"]
                or canonical_title(group.get("event_title")) != canonical_title(evidence["title"])
                or group.get("date") not in evidence["days"]
                or norm(group.get("venue")) != norm(evidence["venue"])):
            continue
        target = urlsplit(evidence["official_detail_url"]).hostname
        if not any(urlsplit(u).hostname == target
                   for u in group.get("source_urls", []) if isinstance(u,str)):
            continue
        return {k:v for k,v in evidence.items() if k not in ("days","source_key","title","venue")}
    return None


def canonical_title(value):
    value=norm(html.unescape(value or ""))
    for composer, title in TITLE_PREFIXES:
        if value.startswith(composer+" ") and (title in value or title == "der fliegende hollander"):
            if title == "der fliegende hollander" and "fliegende" not in value:
                continue
            return title
    return value


# Exact 2026 Pisa productions reconciled against the Teatro di Pisa primary
# programme. A missing venue in the *observation* must never become a certified
# geographic match unless the official source, city, venue and published clock
# all agree. The actual catalogue remains authoritative.
PISA_SOURCE_KEYS = frozenset(("pisa-future-calendar", "pisa-verdi-opera-2026-27"))
PISA_PUBLISHED_ALIASES = {
    "dido and aeneas": "dido and aeneas",
    "dido and æneas": "dido and aeneas",
    "dido and neas": "dido and aeneas",
    "l occasione fa il ladro ossia il cambio della valigia": "l occasione fa il ladro",
    "the turn of the screw il giro di vite": "the turn of the screw",
}
PISA_OFFICIAL_OPERA_LEADS = (
    ("Carmen", ("2026-01-23", "2026-01-25"),
     ("20:30", "15:30"),
     "https://teatrodipisa.it/de/carmen-liberta-e-dionisiaco-nella-nuova-produzione-con-la-regia-di-tonon-e-la-direzione-di-venezi/"),
    ("The turn of the screw (il giro di vite)", ("2026-02-27", "2026-03-01"),
     ("20:30", "15:30"),
     "https://teatrodipisa.it/the-turn-of-the-screw-a-50-anni-dalla-morte-di-britten-per-la-prima-volta-al-teatro-verdi/"),
    ("L’elisir d’amore", ("2026-03-27", "2026-03-29"),
     ("20:30", "15:30"),
     "https://teatrodipisa.it/en/spettacolo/lelisir-damore/"),
)


def official_pisa_source(group):
    from urllib.parse import urlsplit
    return (group.get("source_key") in PISA_SOURCE_KEYS
            and not norm(group.get("venue"))
            and any(urlsplit(url).hostname == "teatrodipisa.it"
                    for url in group.get("source_urls", []) if isinstance(url, str)))


def pisa_published_title(value):
    name = canonical_title(value)
    return PISA_PUBLISHED_ALIASES.get(name, name)


def pisa_catalog_without_observation_venue(group, rows):
    """Recognize only exact published Pisa opera dates, clocks and title aliases."""
    if not official_pisa_source(group):
        return []
    title=pisa_published_title(group.get("event_title"))
    legacy_titles = ("dido and aeneas", "l occasione fa il ladro")
    historical_titles = ("carmen", "the turn of the screw", "l elisir d amore")
    if title not in legacy_titles + historical_titles:
        return []
    # Historical titles require the exact observed official showtime. Merely
    # sharing a common opera title or same city does not prove a match.
    if title in historical_titles and pisa_official_missing_catalog_lead(group) is None:
        return []
    matches=[p for p in rows
             if p["date"]==group.get("date")
             and p["clock"]==group.get("time")
             and norm(p.get("city"))=="pisa"
             and norm(p.get("venue"))=="teatro verdi"
             and pisa_published_title(p.get("title"))==title]
    return matches


def pisa_official_missing_catalog_lead(group):
    """Verified first-party opera observations, NOT permission to publish."""
    if not official_pisa_source(group):
        return None
    for title, days, clocks, official_url in PISA_OFFICIAL_OPERA_LEADS:
        if canonical_title(group.get("event_title")) != canonical_title(title):
            continue
        for day, clock in zip(days,clocks):
            if group.get("date")==day and group.get("time")==clock:
                return {"genre":"opera", "venue":"Teatro Verdi",
                        "official_detail_url":official_url,
                        "reason":"Official Pisa 2025/26 full opera production; not found in the canonical catalog. Needs independent editorial publication review."}
    return None


def catalog_occurrences(catalog):
    rows=[]
    for p in catalog.get("productions", []):
        for d in p.get("dates", []):
            if isinstance(d,list) and len(d)>=1 and isinstance(d[0],str) and d[0].startswith("2026-"):
                rows.append({
                    "date":d[0], "clock":d[1] if len(d)>1 else None,
                    "title":p.get("title"),"venue":p.get("venue"),
                    "city":p.get("municipality"),"source_url":p.get("source_url"),
                })
    return rows


def check(triage, catalog):
    if (triage.get("year") != 2026 or triage.get("read_only") is not True
            or triage.get("catalog_updated") is not False
            or triage.get("complete_seasons_certified") != 0):
        raise ValueError("Invalid source triage")
    if len(triage.get("review_groups",[])) != triage.get("event_groups"):
        raise ValueError("Incomplete triage")
    rows=catalog_occurrences(catalog)
    results=[]
    for g in triage["review_groups"]:
        title=canonical_title(g["event_title"])
        venue=norm(g.get("venue"))
        same_day=[p for p in rows if p["date"]==g["date"]
                  and canonical_title(p["title"])==title
                  and venue and norm(p.get("venue"))==venue
                  and (g["source_key"] not in SOURCE_CITY or
                       norm(p.get("city"))==SOURCE_CITY[g["source_key"]])]
        # Published records can be on a separately corroborated detail URL,
        # while the audit source is a generic theatre index.
        # Same day, work, venue is strong evidence against an automatic
        # "missing" claim but is not proof of exact time matching.
        pisa_confirmed = pisa_catalog_without_observation_venue(g, rows) if not same_day else []
        if pisa_confirmed:
            matches=[{"title":p["title"],"clock":p["clock"],
                      "source_url":p["source_url"],"venue":p["venue"]}
                     for p in pisa_confirmed]
            status="catalog_same_work_day_clock_official_pisa_venue_unprovided"
            evidence=None
        elif same_day:
            matches=[{"title":p["title"],"clock":p["clock"],
                      "source_url":p["source_url"],"venue":p["venue"]}
                     for p in same_day]
            if g.get("time") is not None and any(g["time"]==p["clock"] for p in same_day):
                status="catalog_same_work_day_venue_exact_clock"
            else:
                status="catalog_same_work_day_venue_clock_discrepancy"
            evidence=None
        else:
            matches=[]
            evidence=None
            status="requires_official_genre_and_catalog_review"
            opera_evidence=pisa_official_missing_catalog_lead(g)
            if opera_evidence is not None:
                status="official_opera_unpublished_candidate_first_party_review"
                evidence=opera_evidence
            genre_evidence=official_genre_evidence(g)
            if genre_evidence is not None:
                genre=genre_evidence["genre"]
                if genre=="cancelled_concert":
                    status="official_cancelled_event_first_party"
                elif genre in ("opera_semiscenic_reconstruction",
                               "educational_semi_staged_opera"):
                    status="official_opera_special_format_editorial_review"
                else:
                    status="official_nonopera_first_party_detail"
                evidence=genre_evidence
            for (url, work), decision in OFFICIAL_NONOPERA.items():
                if (g["event_title"]==work and url in g.get("source_urls",[])
                        and g["date"] in decision["days"]):
                    status="official_nonopera_source_scoped"
                    evidence=decision
                    break
        results.append({
            "date":g["date"],"title":g["event_title"],"time":g.get("time"),
            "venue":g.get("venue"),"source_key":g["source_key"],
            "source_urls":g["source_urls"],"triage_bucket":g["bucket"],
            "status":status,"catalog_matches":matches,
            "official_nonopera_evidence":evidence,
            "automatic_publication":False,"automatic_exclusion":False,
        })
    counts=dict(sorted(Counter(r["status"] for r in results).items()))
    by_source={}
    for row in results:
        by_source.setdefault(row["source_key"],Counter())[row["status"]]+=1
    return {
        "schema_version":1,"year":2026,"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,"complete_seasons_certified":0,
        "input_event_groups":len(results),"counts":counts,
        "by_source":{k:dict(sorted(v.items())) for k,v in sorted(by_source.items())},
        "observations":results,
        "warning":"Matching canonical title+day+venue is not proof that the reported clock is correct; preserve conflicts. Any non-opera decision is source-scoped. Other cases need primary-source review. No automatic publication.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    result=check(json.loads(TRIAGE.read_text(encoding="utf-8")),
                 json.loads(CATALOG.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESIDUAL_2026_COUNTERS "+json.dumps(result["counts"],ensure_ascii=False))
    for r in result["observations"]:
        if r["status"]=="catalog_same_work_day_venue_clock_discrepancy":
            print("RESIDUAL_2026_TIME_REVIEW "+json.dumps({
                "date":r["date"],"title":r["title"],"time":r["time"],
                "catalog":r["catalog_matches"],"source":r["source_urls"]
            },ensure_ascii=False))


if __name__=="__main__":
    main()
