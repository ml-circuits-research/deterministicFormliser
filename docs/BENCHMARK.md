# Benchmark real NL → analiză sintactică → CNL

Evaluare locală: 2026-10-07. Toate cele patru backenduri au rulat modele reale pe CPU, în medii Python 3.11 separate. Niciun rezultat de parser nu a fost simulat. Modelele și bibliotecile externe nu au fost modificate.

## Concluzie

Conversia comună în CNL era o sursă majoră de pierdere a informației. Pe 60 de cazuri folosite la diagnosticare, cinci runde de modificări au crescut rata de succes estimată de la 31,7–41,7% la 90–100%, în funcție de parser. Pe 20 de cazuri rezervate, evaluate doar după încheierea modificărilor, rata finală este **75–85%**. Aceasta este estimarea mai relevantă pentru generalizare; nu există dovadă că sistemul are 100% precizie pe texte noi.

CNL rămâne o parafrază controlată, cu acte de vorbire explicite și construcții imbricate păstrate. Nu este o traducere completă în logică formală. Conservarea locală a unui grup nominal, a unei relative sau a unui citat nu înseamnă rezolvarea coreferinței, a elipsei sau a ambiguității. Un arbore nominal care conține aparent toată propoziția nu este declarat o formalizare reușită doar fiindcă permite copierea cuvintelor.

## Metodă și criterii

- 80 de exemple englezești scrise pentru acest experiment: 60 `dev`, 20 `holdout`. Sunt exemple plauzibile și variate, nu un eșantion aleator din trafic real.
- Afirmații, întrebări WH și da/nu, cereri, comenzi negative, interjecții, saluturi, mulțumiri, exclamații, citate, întrebări de confirmare, fragmente, elipse, pasiv, modalitate, negație, cuantificatori, condiționale, relative și fraze lungi cu subordonate multiple.
- Fiecare caz este trimis separat fiecărui parser. Modelele se încarcă o singură dată per proces. O încercare exploratorie cu exemple concatenate a fost abandonată: spaCy unea fragmente din cazuri diferite în jurul citatelor. Acele date nu intră în scoruri.
- Analizele reale au fost înghețate înaintea rundelor. Aceiași octeți de intrare sintactică sunt folosiți în R0–R5; hashurile sunt verificate automat.
- R0 este starea de la începutul benchmarkului extins, **după** remedierile preliminare de instalare și testare pe cele 20 de exemple scurte. Nu este codul inițial al proiectului.
- Fiecare pereche NL/CNL a fost evaluată de asistent. Un caz reușește numai dacă toate propozițiile sale păstrează sensul și actele de vorbire. Diferențele minore de majuscule nu contează; pierderea participanților, negației, condițiilor, timpului, relativelor, citatelor, politeții explicite sau actelor de vorbire contează.
- Rezultatele `failure` și `uncertain` sunt ambele nereușite în rata conservatoare. `coverage` nu determină verdictul semantic.
- Perechile neschimbate între runde își păstrează verdictul; rezultatele modificate sunt revizuite. Nu s-a folosit un scor de similaritate textuală pentru a fabrica etichete semantice.
- Setul rezervat a fost scris de același asistent înaintea rundelor, dar rezultatele lui nu au fost inspectate pentru remediere. După evaluarea lui nu s-a mai modificat rendererul. Autorul cazurilor, implementatorul și evaluatorul sunt același asistent: evaluarea nu este independentă și poate conține erori de judecată.

## Cinci runde pe setul de lucru

Fiecare celulă reprezintă cazuri reușite din 60.

| Parser | R0 | R1 | R2 | R3 | R4 | R5 |
|---|---:|---:|---:|---:|---:|---:|
| Stanza | 23 | 27 | 35 | 49 | 54 | 58 |
| spaCy | 23 | 27 | 35 | 50 | 55 | 57 |
| UDPipe | 19 | 24 | 33 | 46 | 50 | 54 |
| Trankit | 25 | 28 | 37 | 51 | 57 | 60 |

1. **R1 — grupuri nominale, copule, timp:** traversare prin relațiile acceptate, fără determinanți scăpați din subiect în predicat; păstrarea modalelor, complementelor temporale, construcțiilor existențiale și contracțiilor.
2. **R2 — subordonate, relative, citate:** păstrarea poziției relative a subordonatelor, a modificatorilor relativi cu punctuația lor și a granițelor citatelor. Nu se inventează „while” pentru un conector necunoscut.
3. **R3 — acte de vorbire:** întrebări WH din grupuri nominale, comenzi negative, interjecții, saluturi, mulțumiri, exclamații, cereri-fragment și material pragmatic explicit. `FRAGMENT` semnalează absența unui predicat principal în analiză.
4. **R4 — coordonare:** păstrarea grupului de predicate și a auxiliarului/negației comune; eliminarea introducerii nejustificate a lui „either”; păstrarea obiectelor comune, a contrastului și a unor elipse fără inventarea unui verb omis.
5. **R5 — confirmări și contexte speciale:** păstrarea tagurilor de întrebare separat de propoziția principală, a lui `neither`, a focalizării și a copulelor locative din întrebări indirecte; corectarea conjuncției duplicate în elipsă.

Pe cele 240 de combinații caz–parser din `dev`, reușitele cresc de la 90 la 229. Creșterea de 139 de rezultate reușite apare cu **aceleași analize externe**, deci este efectul modificărilor rendererului, în limitele evaluării calitative.

## Rezultatul pe setul rezervat

| Parser | R0, înaintea celor 5 runde | R5, după cele 5 runde |
|---|---:|---:|
| Stanza | 4/20 — 20% | **15/20 — 75%** |
| spaCy | 7/20 — 35% | **15/20 — 75%** |
| UDPipe | 5/20 — 25% | **17/20 — 85%** |
| Trankit | 4/20 — 20% | **15/20 — 75%** |

Total: 20/80 → 62/80 combinații reușite, adică 25% → 77,5%. Cazurile sunt aceleași pentru toate parserele, deci cele 80 de rezultate nu sunt observații independente. Avantajul UDPipe este de numai două cazuri; acest lot nu justifică un clasament general al tehnologiilor.

11 dintre cele 18 nereușite finale au totuși `coverage=1.0`. Modul strict bazat numai pe acoperire nu poate detecta aceste schimbări de sens.

Trankit este cel mai bun pe setul de lucru, însă avantajul dispare pe setul rezervat. Alegerea parserului contează, dar regulile noastre de conversie rămân o limitare importantă.

## Exemple de îmbunătățiri

| NL | CNL inițial | CNL după runde |
|---|---|---|
| The tenant did not sign or return the agreement. | either The tenant did not sign the agreement or The tenant return. | ASSERT: The tenant did not sign or return the agreement. |
| The engineer who inspected the bridge recommended an immediate closure. | ASSERT: The engineer recommended an immediate closure. | ASSERT: The engineer who inspected the bridge recommended an immediate closure. |
| Ouch! | ASSERT: ouch. | EXPRESS: Ouch! |
| You have received the package, haven't you? | ASK WHETHER: You have received the package. | ASK CONFIRM: You have received the package; TAG: haven't you. |

## Eșecuri rămase pe setul rezervat

Atribuirea este o diagnosticare a arborilor, nu o demonstrație că numai componenta indicată ar putea fi schimbată.

| Parser | Caz | Cauză estimată | Problemă |
|---|---|---|---|
| Stanza | h02 | renderer | Relația `advcl:relcl` sub `why` nu este tratată; dispare propoziția despre alarmă. |
| Stanza | h03 | renderer | Obiectul WH este pus înaintea obiectului indirect: `show Which apartment you`. |
| Stanza | h17 | renderer | Se pierde propoziția imbricată și nu se păstrează cererea indirectă. |
| Stanza | h19 | renderer | `Thank you!` devine afirmație; cererea fără `please` devine întrebare de capacitate. |
| Stanza | h20 | renderer | Elipsa imbricată într-un grup nominal pierde participantul Omar. |
| spaCy | h03 | mixt | Parserul produce două subiecte; rendererul păstrează unul și pierde agentul. |
| spaCy | h07 | renderer | Complementul infinitival sub adjectivul `able` este omis. |
| spaCy | h15 | mixt | Parserul pune auxiliarul tagului ca rădăcină; rendererul îl păstrează greșit în propoziția principală. |
| spaCy | h17 | renderer | `even though` devine `though even`; cererea indirectă nu este reprezentată. |
| spaCy | h19 | renderer | Mulțumirea și cererea indirectă sunt etichetate greșit. |
| UDPipe | h04 | mixt | `dose` este atașat ca obiect al lui `patient`; rendererul îl pierde. |
| UDPipe | h17 | mixt | `shipping` devine capul subordonatei; rendererul dublează `even` și schimbă conectorul. |
| UDPipe | h19 | renderer | Mulțumirea și cererea indirectă sunt etichetate greșit. |
| Trankit | h03 | renderer | Aceeași ordine incorectă a obiectelor WH/direct/indirect. |
| Trankit | h08 | parser | Determinantul pentru `players` este atașat lui `coach`: `The coach the`. |
| Trankit | h17 | mixt | Atașare `advcl` pentru `why`, plus conversie incorectă a conectorului și cererii. |
| Trankit | h19 | renderer | Mulțumirea și cererea indirectă sunt etichetate greșit. |
| Trankit | h20 | renderer | Elipsa nominală pierde participantul Omar. |

Din cele 18 nereușite finale: 12 sunt atribuite în principal rendererului, 5 sunt mixte și 1 parserului. Acest lucru corectează impresia de pe `dev`, unde majoritatea nereușitelor finale proveneau din analize externe greșite. **Nu putem afirma că am rezolvat conversia în CNL pentru limbaj liber.**

## Artefacte și reproducere

- Cazuri: `eval/benchmark_cases.json`.
- Criterii: `eval/benchmark/rubric.json`.
- Analize reale și versiuni instalate: `eval/benchmark/*-analyses.json.gz`.
- Cele șase versiuni de renderer: `eval/benchmark/renderer-round-0.py` … `renderer-round-5.py`.
- Fiecare NL, CNL, coverage, avertisment și verdict: `eval/benchmark/*-judged.json`.
- Rate calculate din verdicte: `eval/benchmark/summary.json`.
- Raport HTML filtrabil: `artifacts/benchmark/report.html`, regenerabil prin comanda de mai jos.

```bash
# Recalculează raportul din verdictele păstrate și verifică hashurile.
python3 scripts/report_benchmark.py --verify-replay

# Reproduce exact CNL-ul unei runde fără biblioteci sau modele NLP.
python3 scripts/benchmark.py render --parser stanza --split holdout --round 5 --directory eval/benchmark

# Rulează din nou un parser real într-un director NOU; nu suprascrie analizele înghețate.
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 scripts/benchmark.py parse --parser stanza --split holdout --directory artifacts/new-run
python3 scripts/benchmark.py render --parser stanza --split holdout --round 5 --directory artifacts/new-run

./scripts/selftest.sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 ./scripts/smoke_live.sh
```

Reproducerea CNL-ului și recalcularea ratelor sunt automate. O nouă rulare nu primește automat verdict semantic: acesta necesită o nouă evaluare NL/CNL. Scriptul nu transformă un coverage mare într-un succes semantic.
