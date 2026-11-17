"""DOCX-lay-out van de synthetische cv's: drie varianten (single, table2, header)."""
import tempfile

from docx import Document
from docx.shared import Cm, Pt

from cv_data import L, TODAY

try:
    from PIL import Image, ImageDraw
except ImportError:  # foto's zijn optioneel
    Image = None


def photo_file(rng):
    """Willekeurige 'pasfoto' als PNG; None als Pillow niet geïnstalleerd is."""
    if Image is None:
        return None
    img = Image.new("RGB", (240, 300), (rng.randint(120, 220),) * 3)
    draw = ImageDraw.Draw(img)
    draw.ellipse((70, 50, 170, 150), fill=(90, 90, 90))
    draw.rectangle((50, 170, 190, 300), fill=(90, 90, 90))
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(f.name)
    return f.name


def date_range(job, lang):
    s, e = job["start"], job["end"]
    fe = L[lang]["present"] if e == f"{TODAY:%Y-%m}" else f"{e[5:]}/{e[:4]}"
    return f"{s[5:]}/{s[:4]} - {fe}"


def personal_lines(p):
    fields = p["fields"][1:]  # de naam staat al als titel bovenaan
    if p["labeled"]:
        return [f"{lab}: {val}" for lab, val in fields]
    return [" | ".join(val for _, val in fields)]  # zonder labels = moeilijker voor regels


def job_lines(p, lang):
    out = []
    for j in p["jobs"]:
        out.append((f"{j['title']} - {j['company']} ({date_range(j, lang)})", True))
        out += [(f"• {t}", False) for t in j["tasks"]]
    return out


def build_docx(p, lang, layout, path, rng):
    l = L[lang]
    doc = Document()
    doc.styles["Normal"].font.size = Pt(rng.choice([10, 10.5, 11]))
    name, u = p["fields"][0][1], p["utility"]
    langs_txt = [f"{x['lang']} ({x['level']})" for x in u["languages"]]
    photo = photo_file(rng) if rng.random() < 0.4 else None
    if photo:
        p["sensitive"].append({"category": "photo", "group": "special", "value": "[afbeelding]", "indirect": False})

    def heading(text, parent=None):
        (parent or doc).add_paragraph().add_run(text).bold = True

    def write_jobs(parent=None):
        for text, bold in job_lines(p, lang):
            (parent or doc).add_paragraph().add_run(text).bold = bold

    doc.add_heading(name, 0)
    if layout == "single":
        if photo:
            doc.add_picture(photo, width=Cm(3))
        heading(l["personal"])
        for line in personal_lines(p):
            doc.add_paragraph(line)
        heading(l["profile"]); doc.add_paragraph(p["profile"])
        heading(l["jobs"]); write_jobs()
        heading(l["edu"]); [doc.add_paragraph(e) for e in u["education"]]
        heading(l["skills"]); doc.add_paragraph(", ".join(u["skills"]))
        heading(l["langs"]); doc.add_paragraph(", ".join(langs_txt))
        heading(l["extra"]); [doc.add_paragraph(x) for x in p["extra"]]
    elif layout == "table2":
        t = doc.add_table(rows=1, cols=2)
        left, right = t.rows[0].cells
        if photo:
            left.add_paragraph().add_run().add_picture(photo, width=Cm(3))
        heading(l["personal"], left)
        for line in personal_lines(p):
            left.add_paragraph(line)
        heading(l["skills"], left); left.add_paragraph(", ".join(u["skills"]))
        heading(l["langs"], left); left.add_paragraph(", ".join(langs_txt))
        heading(l["profile"], right); right.add_paragraph(p["profile"])
        heading(l["jobs"], right); write_jobs(right)
        heading(l["edu"], right); [right.add_paragraph(e) for e in u["education"]]
        heading(l["extra"], right); [right.add_paragraph(x) for x in p["extra"]]
    else:  # "header": persoonsgegevens in een tabelkop
        t = doc.add_table(rows=1, cols=2 if photo else 1)
        t.rows[0].cells[0].text = "\n".join(personal_lines(p))
        if photo:
            t.rows[0].cells[1].paragraphs[0].add_run().add_picture(photo, width=Cm(2.5))
        heading(l["profile"]); doc.add_paragraph(p["profile"])
        heading(l["jobs"]); write_jobs()
        heading(l["edu"]); doc.add_paragraph("; ".join(u["education"]))
        heading(l["skills"]); doc.add_paragraph(" · ".join(u["skills"]))
        heading(l["langs"]); doc.add_paragraph(" · ".join(langs_txt))
        heading(l["extra"]); doc.add_paragraph("\n".join(p["extra"]))
    doc.save(path)
