# Experimentlog: redactie van gevoelige gegevens in cv's

## Exp 01-03: baselines op synthetische set (100 cv's, seed 42)

**Vraag**: hoeveel gevoelige gegevens laten regex, NER (spaCy) en hybrid staan?
**Methode**: `evaluate.py --method regex|ner|hybrid`, ground truth uit `cv_generator.py`.
**Data**: `data/synthetic_100` (NL/EN, 3 lay-outs), niet in git; reproduceerbaar met seed 42.

**Resultaten**: zie `vergelijking.md`
- regex en hybrid: 100% recall (645 waarden), 99,6% precision, 0 ervaringsverlies
- NER alleen: 27% recall, 70% precision, `special` 0%

**Iteratie**: eerste run regex gaf 93,4% recall (`archief/exp01_regex_100_v1.json`).
- Meetfout 1: foto's telden als lek in `special` (fix in evaluate.py)
- Meetfout 2: taal "Nederlands" werd als nationaliteitslek geteld (talensectie gemaskeerd)
- Regexfout: Belgisch vast nummer met slash ("02/ 250 58 54"), patroon toegevoegd

**Interpretatie**: 100% is een bovengrens. Regexlijsten en generator gebruiken dezelfde woorden (circulair).

**Beperkingen**
- Over-redactie meet enkel tekens buiten alle ground-truth-spans, geen verkeerde labels
- 2 `national_number`-detecties zijn eigenlijk telefoonnummers (label fout, niets gelekt)
- Foto's niet meegeteld in tekstcijfers

**Beslissing**: regex bevriezen (tag `regex-v1`) en meten op een moeilijkere set.

## Exp 04-06: moeilijke set (200 cv's, seed 7, `--hard`)

**Vraag**: houden regex, NER en hybrid stand op cv's met woorden, labels, formaten en
formuleringen die niet in de regexlijsten staan?
**Verwachting vooraf**: regex zakt sterk, want de lijsten waren afgestemd op de eerste generator.
**Methode**: dezelfde `evaluate.py` en dezelfde regex (tag `regex-v1`, niet aangepast op deze set).
**Data**: `data/hard_200`, gegenereerd met `cv_generator.py --n 200 --seed 7 --hard`.
Elke gevoelige waarde heeft een `variant` (unseen_word, other_phrase, other_label, other_format).
Ongeveer 40% van de cv's bevat een valstrik: een niet-gevoelige regel met een trefwoord
(bijv. "Stichting tegen Kanker").

**Resultaten** (`experiments/exp04-06_*.json`, `vergelijking.md`)

| methode | recall | special | discrim. | identifier | direct | indirect | precision | over-redactie |
|---|---|---|---|---|---|---|---|---|
| regex | 41,4% | 14,7% | 16,6% | 61,3% | 44,7% | 1,0% | 76,3% | 40,2% |
| ner | 20,6% | 0,0% | 6,2% | 33,3% | 22,3% | 0,0% | 62,3% | 26,5% |
| hybrid | 51,3% | 14,7% | 22,7% | 75,4% | 55,4% | 1,0% | 72,8% | 38,6% |

Ervaring in maanden 200/200 juist en 0 verloren skills, voor alle methodes.

**Vergelijking met de makkelijke set**: regex en hybrid zakken van 100% naar 41,4% en 51,3% recall.

**Interpretatie**
- Regex vindt enkel wat een vast patroon of trefwoord heeft (e-mail, naam, rijksregisternummer,
  "n kinderen"). Nationaliteit, burgerlijke staat, religie en vakbond: 0% (woorden buiten de lijsten).
  Adres: 0% (postcode vóór gemeente). Gezondheid, strafregister en indirecte zinnen: bijna niets.
- NER vindt adressen (67% strikt) en een deel van de geboortedata, die regex mist. Daardoor wint
  hybrid ongeveer 10 procentpunten op regex. Op `special` doet NER niets (geen entiteitstype).
- `special` is het gevaarlijkst en het slechtst gedekt (14,7%). Dit motiveert een derde methode
  (lokaal taalmodel) die zinnen zonder vast patroon kan herkennen.

**Bevindingen**
- Het regex-adrespatroon leest "October 28, 1999 in ..." als "huisnummer, postcode" en wist de hele
  zin ervoor mee (11 detecties, 0 juist).
- NER-adres: 208 detecties, 122 juist. Oorzaak van de valse detecties nog niet onderzocht.

**Beperkingen**
- De set is door mij ontworpen, niet uit echte cv's gehaald. De variaties zijn plausibel maar niet bewezen.
- Woorden bewust buiten de lijsten gekozen, dus regex is hier per constructie kwetsbaar. De 41,4% zegt
  iets over gevoeligheid voor onbekende woorden, niet over regex in het algemeen.
- De strikte recall is bij adressen te mild (NER haalt vaak enkel de gemeente weg), de gedeeltelijke
  maat is ruis bij cijferwaarden. Een positionele tekencoverage-maat volgt.
- Informatieverlies is 0 omdat de valstrikken geen skills of functies bevatten. Nog niet meetbaar.
- Over-redactie meet enkel tekens buiten alle ground-truth-spans, geen verkeerde labels.

**Beslissing / volgende stap**
1. Tekencoverage-maat en recall per variant toevoegen aan evaluate.py.
2. Valstrikken met utility toevoegen (functietitel of werkgever met trefwoord), zodat verlies meetbaar wordt.
3. Derde methode (lokaal taalmodel) voorbereiden zodra de hardware duidelijk is.