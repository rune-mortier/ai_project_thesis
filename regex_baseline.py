"""
Regex-baseline voor het detecteren en opschonen van gevoelige gegevens in cv's.

Bewust simpel: enkel reguliere expressies, woordenlijsten en positieheuristieken.
Dit is de ondergrens waartegen NER en het lokale taalmodel later vergeleken worden.

Gebruik als module:
    from regex_baseline import docx_text, docx_has_picture, detect, sanitize
"""
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

SEP = r"[|│]"                       # veldscheiding in cv's zonder labels
END = rf"(?=\s*(?:{SEP}|\n|$))"     # einde van een veld

LABELS = ("E-mail|Email|Telefoon|Phone|Adres|Address|Geboortedatum|Date of birth|Nationaliteit|Nationality|"
          "Burgerlijke staat|Marital status|Kinderen|Children|Rijksregisternr\\.|National number|•")


def _is_zip(path):
    with open(path, "rb") as f:
        return f.read(2) == b"PK"


def _from_text_export(path):
    """Terugval voor tekst-/markdown-exports van een cv (geen echt DOCX).
    Enkel bedoeld om de baseline te kunnen testen op platgeslagen voorbeelden."""
    t = open(path, encoding="utf-8").read().replace("**", "\n")
    t = re.sub(r"^\| | \|$", "", t, flags=re.M).replace("| --- |", "")
    t = re.sub(rf"\s+(?=(?:{LABELS})\b)", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def docx_text(path):
    """Platte tekst in leesvolgorde, inclusief tabellen. Eén alinea per regel."""
    if not _is_zip(path):
        return _from_text_export(path)
    doc = Document(path)
    lines = []
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            lines.append(Paragraph(el, doc).text)
        elif el.tag.endswith("}tbl"):
            for row in Table(el, doc).rows:
                for cell in row.cells:
                    lines.extend(p.text for p in cell.paragraphs)
    return "\n".join(lines)


def docx_has_picture(path):
    """True/False voor een echt DOCX, None als dat niet te bepalen is (tekstexport)."""
    if not _is_zip(path):
        return None
    return len(Document(path).inline_shapes) > 0


# ---------------------------------------------------------------- patronen
NATIONALITIES = ("Belgisch|Nederlands|Pools|Marokkaans|Turks|"
                 "Belgian|Dutch|Polish|Moroccan|Turkish")
MARITAL = "Gehuwd|Ongehuwd|Samenwonend|Gescheiden|Married|Single|Cohabiting|Divorced"
MONTHS = ("januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december|"
          "January|February|March|April|May|June|July|August|September|October|November|December")
HEALTH_KW = "dyslexie|dyslexia|diabetes|burn-out|burnout|rugklachten|back problems|kanker|cancer|depressie|depression"
RELIGION_KW = "parochie|parish|Islamitische|Islamic|kerk|church|moskee|mosque|synagoge|synagogue|tempel|temple"
UNION_KW = "vakbond|trade union|ACV|ABVV|ACLVB"

# (categorie, patroon, vlaggen). Volgorde = prioriteit bij overlap.
PATTERNS = [
    ("national_number", r"(?<!\d)\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}(?!\d)|(?<!\d)\d{11}(?!\d)", 0),
    ("email", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", 0),
    # NL/BE: "Straat 12, 9000 Gent"
    ("address", rf"[^\n|│,:]*? \d{{1,4}}[a-z]?, \d{{4}} [^\n|│]+?{END}", 0),
    # UK: "12 Street Name, AB1C 2DE Plaats"
    ("address", rf"(?<!\w)\d{{1,4}} [^\n|│,:]+, [A-Z]{{1,2}}\d[A-Z\d]? ?\d[A-Z]{{2}} [^\n|│]+?{END}", 0),
    # indirecte familiezin (hele zin)
    ("family", r"[^.\n]*\b(?:Als (?:vader|moeder) van \d+ kinderen|As an? (?:father|mother) of \d+ children)[^.\n]*\.?", 0),
    ("health", rf"[^.\n]*\b(?:{HEALTH_KW})\b[^.\n]*\.?", re.I),
    ("criminal_record", r"[^.\n]*\b(?:Veroordeeld|Convicted|strafblad|criminal record)\b[^.\n]*\.?", 0),
    ("religion", rf"[^\n]*\b(?:{RELIGION_KW})\b[^\n]*", re.I),
    ("union", rf"[^\n]*\b(?:{UNION_KW})\b[^\n]*", re.I),
    ("birth_date", rf"(?<![\d/.])\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{4}}(?![\d/.])|\b\d{{1,2}} (?:{MONTHS}) \d{{4}}\b", 0),
    # Belgisch vast nummer met slash: "02/ 250 58 54"
    ("phone", r"(?<![\w./])0\d{1,2}/ ?\d{2,3}(?: ?\d{2}){2,3}(?!\d)", 0),
    # telefoon: +32.., +44(0).., (0121)4960750, 0437-770818
    ("phone", r"(?<![\w.])(?:\+\d{2}\s?(?:\(0\))?|\(?0)[\d\s\-()]{7,}\d", 0),
    # nationaliteit: met label, of als los veld (anders botst het met talen: "Nederlands (moedertaal)")
    ("nationality", rf"(?<=Nationaliteit: )(?:{NATIONALITIES})|(?<=Nationality: )(?:{NATIONALITIES})"
                    rf"|(?:(?<=^)|(?<=[|│] ))(?:{NATIONALITIES}){END}", re.M),
    ("marital_status", rf"\b(?:{MARITAL})\b", 0),
    ("family", r"\b\d+ (?:kinderen|kind|children|child)\b", 0),
]
COMPILED = [(cat, re.compile(p, f)) for cat, p, f in PATTERNS]


def _overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def detect(text):
    """Geeft lijst van (start, einde, categorie, tekst). Eerste patroon wint bij overlap."""
    found = []
    # naam: eerste niet-lege regel (titel van het cv); regex kan een naam niet herkennen
    m = re.search(r"\S[^\n]*", text)
    if m:
        found.append((m.start(), m.end(), "name", m.group().rstrip()))
    for cat, rx in COMPILED:
        for m in rx.finditer(text):
            s, e = m.start(), m.end()
            while e > s and text[e - 1] in " \t":  # geen witruimte aan de randen meenemen
                e -= 1
            while s < e and text[s] in " \t":
                s += 1
            if e <= s:
                continue
            if any(_overlaps((s, e), (a, b)) for a, b, *_ in found):
                continue
            found.append((s, e, cat, text[s:e]))
    return sorted(found)


def sanitize(text, detections=None):
    """Vervang elke detectie door [CATEGORIE]."""
    detections = detect(text) if detections is None else detections
    out, pos = [], 0
    for s, e, cat, _ in detections:
        out.append(text[pos:s])
        out.append(f"[{cat.upper()}]")
        pos = e
    out.append(text[pos:])
    return "".join(out)


if __name__ == "__main__":
    import sys
    t = docx_text(sys.argv[1])
    for s, e, cat, val in detect(t):
        print(f"{cat:16} {val!r}")
    print("\n--- opgeschoond ---\n" + sanitize(t))