# Salerno — Teatro Municipale Giuseppe Verdi, stagione lirica 2026

Indice ufficiale: https://cultura.comune.salerno.it/teatro-verdi/la-stagione/
Le sei produzioni liriche/operettistiche incluse sono Il trovatore, Il signor
Bruschino, Il barbiere di Siviglia, Macbeth, La vedova allegra e Turandot.
Le due schede di danza (Carmen e La vie en rose/Bolero) sono escluse.
I dettagli sono letti soltanto da /eventi/<slug>-2026/ sullo stesso host,
con parser che verifica titolo, compositore, sede, giorno della settimana,
data e orario da APPUNTAMENTI. La prima verifica live non è ancora attestata.

Robots.txt resta obbligatorio per ogni richiesta (fail closed).
Le candidate confluiscono nella riconciliazione unica, senza cataloghi
separati o nuovi deploy FTP. La fonte 2026 non garantisce già la stagione
2027: il nuovo programma dovrà essere verificato e configurato.

## Comportamenti da testare
- python -m unittest tests.test_salerno_opera_source -v
- python -m unittest discover -s tests -v
- python -m scripts.source_automation --check
- Verificare dopo il merge in season-index-health.json la fonte
  salerno-verdi-opera-2026 e le sei candidate ufficiali.
- Verificare negli evidence dettagliati gli orari di Turandot:
  21 e 23 dicembre 2026 ore 21, 26 dicembre ore 18.
- Escludere i due balletti, le recite delle scuole e gli URL esterni;
  non contare come pubblicate date non ancora promosse nei JSON canonici.
