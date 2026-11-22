# Sassari — Ente Concerti Marialisa de Carolis, stagione 2026

Indice ufficiale: https://www.marialisadecarolis.it/opere-liriche.aspx

Il programma comprende opere a Sassari e rappresentazioni
nell'Alghero Festival. Questo connettore censisce **solo** i tre
spettacoli attribuiti al Teatro Comunale di Sassari, senza
confondere l'organizzatore con il luogo della recita:
- Il flauto magico di W. A. Mozart (id=372): 25 settembre ore 20:30,
  27 settembre ore 16:30.
- Don Carlo di Giuseppe Verdi (id=373): 30 ottobre ore 20:30,
  1 novembre ore 16:30.
- Rigoletto di Giuseppe Verdi (id=375): 11 dicembre ore 20:30,
  13 dicembre ore 16:30.

Le date si riferiscono al 2026. Nel calendario compaiono anche
L'elisir d'amore (id=370) e Pagliacci (id=371), ma tali spettacoli
sono all'Alghero Festival, Forte della Maddalena, e **non**
devono essere pubblicati come recite del Teatro Comunale.
Esclusi anche Sinfonia n. 3 di Mahler e Concerto di Natale.

Il parser approva esclusivamente tre query ASP esatte e conferma
titolo, compositore, due orari individuali e venue entro il
contenuto della scheda, non nel menu condiviso. Non assume
il cartellone 2027 sulla base della stagione 2026.
La pipeline centrale gestisce identita', recensioni e pubblicazione:
i risultati rimangono candidate finché il refresh live non conferma
le singole recite.

## Comportamenti da testare

- python -m unittest tests.test_sassari_de_carolis_source -v
- python -m unittest discover -s tests -v
- python -m scripts.source_automation --check
- Verificare tre URL ufficiali, sei orari, venue Sassari e
  l'assenza di Alghero e concerti nel catalogo di Sassari.
