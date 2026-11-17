# Experiment 2 — NER (spaCy) als tweede arm van de vergelijking

Datum: 05/11/2026 · Rune Mortier · thesis "privacylaag voor cv-screening" (Crops)

## 1. Vraag en hypothese

**Vraag.** Hoeveel beter dan een regelgebaseerde opschoner haalt een NER-bibliotheek
(spaCy) gevoelige gegevens uit Nederlandse en Engelse cv's, en wat kost dat aan bruikbare
informatie voor de screening?

**Hypothese.** NER wint op vrije tekst (indirecte lekken zoals "Vrijwilliger bij de parochie
van Gent"), maar verliest op gestructureerde velden, waar regels met labels en patronen
sterker zijn. De combinatie (hybride) zou daarom het beste van beide moeten halen.

## 2. Methode

Drie configuraties, alle drie op dezelfde teksten en met dezelfde meetlat
(`evaluate.py`):

| methode | wat het doet |
|---|---|
| `regex` | `regex_baseline.py`: patronen, woordenlijsten en positieheuristieken (bestaande baseline) |
| `ner` | `ner_baseline.py`: enkel spaCy (`nl_core_news_sm` / `en_core_web_sm`), zonder enige regel |
| `hybrid` | `regex_baseline ∪ ner`: wat de regex al vindt, wint; NER vult aan waar de regex niets ziet |

Bewuste ontwerpkeuzes in de NER-arm, nodig om de vergelijking eerlijk te houden:

1. **Taalherkenning** op de sectiekopjes (bv. "Geboortedatum" vs. "Date of birth"), zodat
   het juiste model wordt geladen.
2. **Persoonsblok begrensd.** Alles vóór de eerste sectiekop (profiel, werkervaring,
   opleiding, vaardigheden, talen, interesses) is "kop". Alleen daar tellen `DATE` en
   `GPE/LOC/FAC`. Zonder die grens zou een `DATE` bij een werkperiode
   (`03/2019 - 06/2022`) de ervaringsberekening breken, en een `ORG`/`PERSON` in de
   inhoud zou een werkgever of contactpersoon wissen. Dat is meteen de prijs van NER:
   ze weet niet *waarom* een datum in de tekst staat.
3. **`PERSON` alleen als titel** (eerste drie niet-lege regels). Elders is een naam
   evengoed een werkgever of een referentie.
4. **Filter op echte datums.** De kleine modellen taggen huisnummers en postcodes
   ("4642") als `DATE`; enkel datumvormen met scheidingstekens, maandnaam of een
   compacte 6-8 cijferige datum tellen.
5. **Filter op veldlabels.** Dezelfde modellen taggen de labels zelf ("Adres",
   "Telefoon", "E-mail") als locatie. Die woorden zijn geen gevoelige waarde.

Voor de precisie- en lekmeting is `evaluate.py` uitgebreid met drie dingen:

- **streng vs. gedeeltelijk lek**: een waarde telt ook als lek wanneer minstens de helft
  van haar tokens nog in de tekst staat. Zonder die maatstaf zou een detectie die enkel
  de gemeente uit een adres haalt als "geen lek" tellen.
- **direct vs. indirect** lek, op basis van de `indirect`-vlag in de ground truth.
- **`--method`**, zodat alle drie de armen door exact dezelfde code worden gemeten.

## 3. Data

`data/synthetic_100`: 100 synthetische cv's, seed 42, gegenereerd door `cv_generator.py`
(afwisselend NL/EN, drie lay-outs, labels soms weggelaten, foto in 39 gevallen).
684 gelabelde gevoelige waarden in totaal: 123 bijzondere, 199 discriminatoire,
362 identificatoren. 46 daarvan zijn *indirect* (bv. een parochie in
vrijwilligerswerk verraadt religie).

**Reproduceerbaarheid gecontroleerd.** De regex-arm op deze verse set geeft exact dezelfde
cijfers als de bestaande `experiments/exp01_regex_baseline.json` (45 lekken op 684,
over-redactie 0,0%, 100/100 maanden juist). De generator en de oude run zijn dus
reproduceerbaar; de vergelijking hieronder staat op dezelfde data.

## 4. Resultaten (100 cv's)

| methode | recall (micro) | bijzonder | discriminatie | identificatoren | precision (micro) | over-redactie | maanden juist | skills verloren |
|---|---|---|---|---|---|---|---|---|
| regex | 93,4% | 68,3% | 98,5% | 99,2% | 99,6% | 0,0% | 100/100 | 0 |
| ner | 25,4% | 0,0% | 20,6% | 36,7% | 70,2% | 0,0% | 100/100 | 0 |
| hybrid | 93,4% | 68,3% | 98,5% | 99,2% | 99,6% | 0,0% | 100/100 | 0 |

Recall naar aard van het lek:

| methode | direct (599) | indirect (46) |
|---|---|---|
| regex | 99,0% | 100% |
| ner | 29,0% | 0,0% |
| hybrid | 99,0% | 100% |

Per categorie (recall) waar de armen verschillen:

| categorie | n | regex | ner |
|---|---|---|---|
| naam | 100 | 100% | 68,0% |
| adres | 77 | 100% | 53,2% |
| geboortedatum | 68 | 100% | 54,4% |
| telefoon | 85 | 96,5% | 21,2% |
| e-mail | 100 | 100% | 6,0% |
| nationaliteit | 39 | 92,3% | 7,7% |
| gezin, gezondheid, religie, vakbond, strafregister, rijksregisternr. | 113 | 100% | 0,0% |
| foto | 39 | 0,0% | 0,0% |

## 5. Interpretatie

1. **Zuivere NER is op deze data geen alternatief voor regels** (25,4% recall). De kleine
   modellen hebben geen entiteitstypes voor e-mail, telefoon, nationaliteit,
   gezinssituatie, gezondheid, religie of strafregister. Alles wat in een *gestructureerd
   veld* staat, valt weg — precies de categorie waar de grootste aantallen zitten.
2. **De hybride arm voegt niets toe, en dat is het interessantste resultaat.** De regex
   haalt 100% op naam, adres en geboortedatum, dus elke NER-detectie valt binnen een
   bestaande regex-span en wordt bij het samenvoegen weggefilterd. De vergelijking is
   *verzadigd*: op deze dataset kan NER niets bewijzen.
3. **De hypothese over indirecte lekken wordt niet bevestigd**, omdat de regex ze al
   vangt: de generator gebruikt vaste formuleringen ("Vrijwilliger bij de parochie van
   {stad}", "Als vader van {n} kinderen"), en de baseline heeft daar woordenlijsten en
   zinsfilters voor. Er zit dus geen echt "nieuw" taalgebruik in de testset.
4. **Foto's blijven in alle armen staan** (39/39). Een tekstpijplijn kan een afbeelding
   niet verwijderen; dat moet een aparte stap in de extractie zijn. Dit is een
   aanbeveling voor het project, niet een modelprobleem.
5. **Wat overblijft zijn twee kleine tekstfouten** (nationaliteit 3/39, telefoon 3/85);
   daar zit de echte ruimte voor verbetering, niet in de grote categorieën.
6. **De precisie van NER (70,2%) verbergt een tweede probleem**: bijna een derde van haar
   detecties heeft de verkeerde categorie (een postcode als geboortedatum, een
   straatnaam als gemeente). De over-redactie blijft 0,0% omdat die spans toch binnen
   een echte adresspan vallen — een metric die dus *te mild* is voor categoriefouten.
   Voor de thesis: precision per categorie rapporteren, niet enkel over-redactie.

## 6. Beperkingen en threats to validity

- **Co-design van data en baseline.** De generator en `regex_baseline.py` zijn door
  dezelfde persoon en in dezelfde stijl geschreven. De baseline is dus kunstmatig sterk
  op deze set; op echte cv's met vrije formuleringen zal ze zakken. Dit is de grootste
  bedreiging voor de geldigheid van de vergelijking en meteen het argument om
  geanonimiseerde voorbeelden bij Crops te vragen.
- **Synthetische cv's zijn te makkelijk** (staat ook als risico in het research
  contract): vaste zinsbouw, vaste datumnotatie, vaste labels.
- **Kleine modellen.** `*_sm` is de kleinste variant; een groter model (`*_lg`, of een
  transformer-NER) kan beter scoren. Vastgelegd als vervolgmeting, niet als excuus.
- **De kop-grens is een ontwerpkeuze**, geen eigenschap van NER. Een pipeline die NER
  over de volledige tekst laat lopen, haalt meer recall maar wist ook werkgevers en
  werkperiodes — dat is een afweging die apart gemeten moet worden.
- **`evaluate.py` meet recall op exacte waarden** en precision via overlap met de
  ground truth; een gedeeltelijke redactie wordt met de nieuwe gedeeltelijke-lekmeting
  opgevangen, maar blijft een benadering.

## 7. Beslissing en impact op het project

- Voor de Crops-pijplijn: **regels blijven de basis** voor gestructureerde velden
  (kopblok, e-mail, telefoon, rijksregisternummer, datums). NER is geen vervanging.
- **Foto's moeten expliciet uit de extractie**, anders lekt 100% van de foto's door naar
  het model. Dit is een concrete eis voor het team (privacyvoorwaarde P03 van Crops).
- De volgende stap in de thesis is **geen vierde arm, maar een zwaardere testset**:
  herschreven vrije tekst, cv's zonder labels, en geanonimiseerde voorbeelden van Crops.
  Pas dan kan het lokale taalmodel een verschil maken, want daar ligt het vermoeden dat
  het *indirecte* en vrij geformuleerde lekken wél vangt.

## 8. Reproductie

```bash
# eenmalig
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m spacy download nl_core_news_sm
./.venv/Scripts/python.exe -m spacy download en_core_web_sm

# dataset (deterministisch, seed 42)
./.venv/Scripts/python.exe cv_generator.py --n 100 --seed 42 --out data/synthetic_100

# drie armen
./.venv/Scripts/python.exe evaluate.py --data data/synthetic_100 --method regex  --out experiments/exp01_regex_100.json
./.venv/Scripts/python.exe evaluate.py --data data/synthetic_100 --method ner    --out experiments/exp02_ner_100.json
./.venv/Scripts/python.exe evaluate.py --data data/synthetic_100 --method hybrid --out experiments/exp03_hybrid_100.json

# vergelijkingstabel (markdown)
./.venv/Scripts/python.exe compare_experiments.py --out experiments/vergelijking.md
```

**Interpreter.** Alle commando's hierboven gaan via `.venv`. Draai je per ongeluk met de
conda-basis (`python`), dan faalt de import al met `ModuleNotFoundError: No module named
'docx'` of `'spacy'` — dat is geen modelfout maar een verkeerde interpreter. Kies in de
editor `thesis/.venv` als interpreter (Ctrl+Shift+P → *Python: Select Interpreter*).
Het model wordt één keer geladen bij de eerste `detect()`-aanroep (gemeten: 4,6 s voor
beide modellen samen) en daarna hergebruikt via `lru_cache`.

Artefacten: `experiments/exp01_regex_100.json`, `exp02_ner_100.json`,
`exp03_hybrid_100.json`, `vergelijking.md`.

Code, opgesplitst per verantwoordelijkheid (elk bestand onder 200 regels):
`cv_data.py` (vaste tabellen en labels) · `cv_generator.py` (profiel + CLI) ·
`cv_docx.py` (de drie lay-outs) · `regex_baseline.py` · `ner_baseline.py` (detectie en
hybride) · `evaluate.py` (meting) · `eval_report.py` (tabellen) ·
`compare_experiments.py` (vergelijking).

## 9. Technische notities (voor verdediging)

- In de eerste hybride run was de recall *lager* dan die van regex (71,6%). Oorzaak: de
  NER-spans werden achteraan aan de lijst toegevoegd terwijl `sanitize` de tekst van
  links naar rechts in stukken knipt, waardoor de uitvoertekst verminkte. Opgelost door
  op positie te sorteren in `_merge`; cijfers hierboven zijn van na de fix.
- De eerste NER-run (zonder de filters uit §2) gaf 33,8% recall maar verloor 4,8
  procentpunt skills: in de `table2`-lay-out stond de skills-sectie nog binnen het
  persoonsblok. `HEADING` is uitgebreid met vaardigheden/talen/interesses, waarna het
  verlies 0 werd. Beide fouten zijn met de hand teruggevonden via
  `experiments/vergelijking.md` en de diagnoserun, niet automatisch.
