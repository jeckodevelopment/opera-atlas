# Teatro Goldoni di Firenze: sede distinta e verificata

Il calendario ufficiale del Maggio Musicale Fiorentino indica **Teatro Goldoni**, ma esiste un altro Teatro Goldoni a Livorno. L'identità di una sede è sempre città + nome + indirizzo, non il solo nome.

Il Teatro Goldoni di Firenze è in Via Santa Maria 15, in Oltrarno; fu inaugurato il 7 aprile 1817 e venne usato anche come teatro di corte per la vicinanza a Palazzo Pitti. Fonte istituzionale: https://www.maggiofiorentino.com/teatri-2/ e https://www.maggiofiorentino.com/come-raggiungerci-2-2/. L'immagine è una fotografia reale della facciata di Sailko, conservata su Wikimedia Commons, con licenza CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:Teatro_goldoni_firenze.JPG.

La nuova scheda usa la route `firenze/teatro-goldoni` e l'identità editoriale `Firenze|Teatro Goldoni`, separatamente dal già censito `livorno/teatro-goldoni`. Il connettore del Maggio ammette il Goldoni di Firenze soltanto con crediti e date ufficiali; quando una rappresentazione verificata lo rende canonico, la registrazione avviene senza identificare erroneamente il teatro livornese.

I dati editoriali sono sincronizzati nei registri sorgente `data/venue-directory.json`, `site/theatre-profiles.json` e nel feed pubblico `public/catalog/venue-directory.json`. Non si pubblicano copertine generative, indirizzi ipotetici o riassunti anagrafici segnaposto. Verifiche: `python -m unittest discover -s tests -v`, inclusi test sui due teatri omonimi e sulla convalida della sede.
