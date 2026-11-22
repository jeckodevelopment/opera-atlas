# Lecce — Teatro Apollo, Le avventure di Pinocchio (2026)

Fonte primaria della Provincia di Lecce:
https://www.provincia.le.it/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/

Il cartellone della **51ª Stagione lirica della Provincia di Lecce**
contiene tre opere al **Teatro Politeama Greco** (già coperte da un
connettore indipendente) e un'opera contemporanea *fuori abbonamento*
al **Teatro Apollo**. Non sono produzioni nella medesima sede.

La pagina ufficiale attribuisce *Le avventure di Pinocchio* ad
**Antonio Cericola**, su libretto di Sandro Bernabei, e indica una
rappresentazione il **30 dicembre 2026 alle ore 20:45** presso
il Teatro Apollo di Lecce.

Questo adattatore accetta soltanto l'URL ufficiale esatto e richiede
nell'HTML la sezione dedicata a *Le avventure di Pinocchio* con
compositore, sede, giorno e ora espliciti. Non converte in recite
all'Apollo le rappresentazioni di Turandot, L'elisir d'amore o Nabucco.

Se il sistema non dispone ancora di un'identità canonica univoca per
quest'opera contemporanea, la candidate resta in revisione e non viene
promossa automaticamente ad una diversa opera omonima.
L'eventuale creazione dell'identità e la sinossi breve rimangono
nella pipeline centralizzata. Come ogni fonte, soggetta a HTTPS,
robots.txt e controllo dei redirect.

## Comportamenti da testare

- `python -m unittest tests.test_lecce_apollo_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Nella prima scansione controllare fonte e un solo evento candidato
  alla sede Apollo. Distinguere dalla pubblicazione canonica e
  verificare l'identità dell'opera di Antonio Cericola.
