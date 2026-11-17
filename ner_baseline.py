"""
NER-arm van de vergelijking: spaCy in plaats van enkel regels.

  ner     : enkel de statistische NER van spaCy (nl_core_news_sm / en_core_web_sm).
            Geen enkele regel. Wat spaCy niet als entiteit herkent, blijft staan.
  hybrid  : de regex-baseline PLUS de NER-detecties die de regex niet al vond. Bij overlap
            wint het hoogste risico (special > discriminatory > identifier), zodat een brede
            NER-span nooit een scherpe regex-span vervangt.

Waarom geen Presidio: dat is een wrapper rond dezelfde modellen met eigen regelgebaseerde
recognizers (e-mail, telefoon, IBAN). De vergelijking met de regex-baseline zou dan
vertroebelen, want Presidio doet zelf ook regex.

Gebruik: python ner_baseline.py data/synthetic_100/cv_001.docx [--method ner|hybrid] [--full]
"""
import re
from functools import lru_cache

from regex_baseline import detect as regex_detect
from regex_baseline import docx_has_picture, docx_text  # noqa: F401  (zelfde interface)

MODELS = {"nl": "nl_core_news_sm", "en": "en_core_web_sm"}

# Taalherkenning op de sectiekopjes: een cv is kort, maar die zijn eenduidig.
NL_HINTS = ("geboortedatum", "nationaliteit", "burgerlijke staat", "kinderen", "werkervaring", "opleiding",
            "vaardigheden", "talen", "heden", "adres", "telefoon", "rijksregisternr", "vrijwilligerswerk",
            "interesses", "persoonlijke gegevens", "profiel")
EN_HINTS = ("date of birth", "nationality", "marital status", "children", "work experience", "education",
            "skills", "languages", "present", "address", "phone", "national number", "volunteering",
            "interests", "personal details", "profile")

# Risicogroep per categorie: lager getal = eerst maskeren bij overlap.
RISK = {"health": 0, "criminal_record": 0, "religion": 0, "union": 0, "national_number": 0, "photo": 0,
        "birth_date": 1, "nationality": 1, "marital_status": 1, "family": 1,
        "name": 2, "email": 2, "phone": 2, "address": 2}

# Einde van het persoonsblok: alles daarvóór is kop, alles erna is inhoud.
HEADING = re.compile(r"(?im)^\s*(profiel|profile|werkervaring|work experience|opleiding|education|"
                     r"vaardigheden|skills|talen|languages|vrijwilligerswerk|volunteering|"
                     r"interesses|interests)\s*$")

# De kleine modellen taggen de veldlabels zelf als locatie ("Adres", "Telefoon").
LABEL_WORDS = {"adres", "address", "telefoon", "phone", "e-mail", "email", "geboortedatum", "date of birth",
               "nationaliteit", "nationality", "burgerlijke staat", "marital status", "kinderen", "children",
               "rijksregisternr.", "national number", "persoonlijke gegevens", "personal details",
               "profiel", "profile"}

# Een echte datum, geen postcode of huisnummer: cijfers met scheidingstekens, een
# dag-maand-jaar met maandnaam, of een compacte 6-8 cijferige datum (19930121).
DATE_SHAPE = re.compile(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\b\d{1,2}\s+\w+\s+\d{4}\b|\b\d{6,8}\b")


def guess_lang(text):
    """'nl' of 'en' op basis van de sectiekopjes in de tekst."""
    t = " " + re.sub(r"\s+", " ", text.lower()) + " "
    return "nl" if sum(w in t for w in NL_HINTS) >= sum(w in t for w in EN_HINTS) else "en"


@lru_cache(maxsize=2)
def _nlp(lang):
    """Laad het model één keer per taal; lru_cache hergebruikt het daarna (gemeten: 4,6 s)."""
    try:
        import spacy
    except ImportError as exc:
        raise SystemExit("spaCy staat niet in deze interpreter. Gebruik de thesis-venv:\n"
                         "  ./.venv/Scripts/python.exe -m pip install -r requirements.txt\n"
                         "of kies thesis/.venv als interpreter in je editor.") from exc
    try:
        return spacy.load(MODELS[lang])
    except OSError as exc:  # model nog niet gedownloadd
        raise SystemExit(f"Model {MODELS[lang]!r} ontbreekt. Download het met:\n"
                         f"  ./.venv/Scripts/python.exe -m spacy download {MODELS[lang]}") from exc


def _head_end(text):
    """Positie waar het persoonsblok eindigt (of het einde van de eerste 1000 tekens)."""
    m = HEADING.search(text)
    return m.start() if m else min(len(text), 1000)


def _first_lines(text, n=3):
    """(start, einde) van de eerste n niet-lege regels: daar staat de naam als titel."""
    out, pos = [], 0
    for line in text.split("\n")[:12]:
        stripped = line.strip()
        if stripped:
            start = pos + line.index(stripped)
            out.append((start, start + len(stripped)))
            if len(out) >= n:
                break
        pos += len(line) + 1
    return out


def _tidy(spans, text):
    """Witruimte wegstrippen, lege spans weg, hoogste risico wint bij overlap."""
    out = []
    for s, e, cat in spans:
        while s < e and text[s] in " \t\n":
            s += 1
        while e > s and text[e - 1] in " \t\n":
            e -= 1
        if e > s:
            out.append((s, e, cat))
    out.sort(key=lambda x: (RISK.get(x[2], 3), x[0]))
    keep = []
    for s, e, cat in out:
        if not any(s < kb and ks < e for ks, kb, _ in keep):
            keep.append((s, e, cat))
    return sorted(keep)


def ner_detect(text, lang=None):
    """Detecties uit spaCy alleen, als (start, einde, categorie).

    Bewuste beperkingen, die meteen de zwakte van deze arm zijn:
      - PERSON telt enkel in de eerste regels (de titel). Elders is een persoonsnaam
        evengoed een werkgever of contactpersoon, en dat mag niet weg.
      - DATE telt enkel in het persoonsblok (vóór de eerste sectiekop), want de
        maandperiodes bij werkervaring zien er hetzelfde uit maar zijn nodig.
      - GPE/LOC/FAC in het persoonsblok gelden als adresgemeente.
      - E-mail, telefoon, rijksregisternummer, nationaliteit, gezinssituatie en gezondheid
        hebben geen entiteitstype in deze modellen: die blijven staan.
    """
    doc = _nlp(lang or guess_lang(text))(text)
    head_end, title, found = _head_end(text), _first_lines(text), []
    for ent in doc.ents:
        s, e = ent.start_char, ent.end_char
        if ent.label_ == "PERSON" and any(h_start <= s and e <= h_end for h_start, h_end in title):
            found.append((s, e, "name"))
        elif ent.label_ == "DATE" and e <= head_end:
            if DATE_SHAPE.fullmatch(ent.text.strip()):
                found.append((s, e, "birth_date"))
        elif ent.label_ in ("GPE", "LOC", "FAC") and e <= head_end:
            if ent.text.strip().lower() not in LABEL_WORDS:
                found.append((s, e, "address"))
    return _tidy(found, text)


def _merge(regex_spans, ner_spans):
    """Regex eerst, dan de NER-spans die geen bestaande detectie overlappen.

    Het resultaat wordt op positie gesorteerd: sanitize knipt de tekst sequentieel in
    stukken en gaat ervan uit dat de spans van links naar rechts komen.
    """
    merged = [(s, e, cat) for s, e, cat, _ in regex_spans]
    for s, e, cat in ner_spans:
        if not any(s < b and a < e for a, b, *_ in merged):
            merged.append((s, e, cat))
    return sorted(merged)


def detect(text, method="hybrid", lang=None):
    """Lijst van (start, einde, categorie, tekst) — zelfde vorm als regex_baseline.detect."""
    if method == "regex":
        return regex_detect(text)
    spans = ner_detect(text, lang)
    if method == "ner":
        chosen = spans
    elif method == "hybrid":
        chosen = _merge(regex_detect(text), spans)
    else:
        raise ValueError(f"onbekende methode: {method!r} (kies regex, ner of hybrid)")
    return [(s, e, cat, text[s:e]) for s, e, cat in chosen]


def sanitize(text, detections=None, method="hybrid"):
    """Vervang elke detectie door [CATEGORIE]."""
    detections = detect(text, method) if detections is None else detections
    out, pos = [], 0
    for s, e, cat, _ in detections:
        out.append(text[pos:s])
        out.append(f"[{cat.upper()}]")
        pos = e
    out.append(text[pos:])
    return "".join(out)


def photo_present(path):
    """Foto's blijven buiten de tekstextractie; dit maakt het verlies meetbaar."""
    return docx_has_picture(path)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--method", default="hybrid", choices=("regex", "ner", "hybrid"))
    ap.add_argument("--full", action="store_true", help="ook de opgeschoonde tekst tonen")
    a = ap.parse_args()
    raw = docx_text(a.path)
    print(f"taal: {guess_lang(raw)}   methode: {a.method}")
    for s, e, cat, val in detect(raw, a.method):
        print(f"{cat:16} {val!r}")
    if a.full:
        print("\n--- opgeschoond ---\n" + sanitize(raw, method=a.method))
