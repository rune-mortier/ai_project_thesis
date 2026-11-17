"""
Generator voor synthetische cv's (NL/EN) met ground truth.

Per cv: cv_NNN.docx (3 lay-outs, labels aan/uit, optionele foto) + cv_NNN.json met
  "sensitive": elke gevoelige waarde EXACT zoals ze in de tekst staat
  "utility":   feiten die het screeningsmodel nodig heeft (maanden ervaring, skills,
               talen, opleiding)
Tabellen staan in cv_data.py, de lay-out in cv_docx.py.

Gebruik: python cv_generator.py --n 100 --seed 42 --out data/synthetic_100
Alle gegevens zijn fictief; het rijksregisternummer is checksum-geldig maar willekeurig.
"""
import argparse
import json
import random
import re
import unicodedata
from datetime import date
from pathlib import Path

from faker import Faker

from cv_data import (CHILDREN, CONDITIONS, CRIME, EDU, FAMILY, FAMILY_W, HEALTH, JOBS, L, LANGS,
                     LEVELS, LOCALES, MARITAL, MONTHS, NATIONALITY, RELIGION, SKILLS, TODAY, UNION)
from cv_docx import build_docx
from cv_data_hard import (HARD_BORN, HARD_CONDITIONS, HARD_CRIME, HARD_FAMILY, HARD_HEALTH, HARD_LABELS,
                          HARD_MARITAL, HARD_NATIONALITY, HARD_RELIGION, HARD_TRAPS, HARD_UNION,
                          hard_address, hard_date, hard_phone)


def fmt_date(d, lang, style):
    if style == 0:
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    if style == 1:
        return f"{d.day}.{d.month}.{d.year}"
    return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


def rijksregisternummer(d, rng, male, formatted):
    seq = rng.randrange(1, 499) * 2 + (1 if male else 0)  # oneven = man, even = vrouw
    base = f"{d:%y%m%d}{seq:03d}"
    check = 97 - (int(("2" if d.year >= 2000 else "") + base) % 97)
    return f"{d:%y}.{d:%m}.{d:%d}-{seq:03d}.{check:02d}" if formatted else f"{base}{check:02d}"


def make_email(first, last, rng, fake):
    strip = lambda t: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode())
    f, l = strip(first), strip(last)
    local = rng.choice([f"{f}.{l}", f"{f}{l}", f"{f[0]}.{l}", f"{f}.{l}{rng.randint(1, 99)}"])
    return f"{local}@{fake.free_email_domain()}"


def make_address(fake, rng, lang, city):
    street, nr = fake.street_name(), rng.randint(1, 180)
    line = f"{street} {nr}" if lang == "nl" else f"{nr} {street}"
    return f"{line}, {fake.postcode()} {city}"


def make_languages(rng, lang):
    chosen = rng.sample(LANGS[lang], rng.randint(2, 3))
    native = rng.randrange(len(chosen))  # precies één moedertaal
    return [{"lang": lg, "level": LEVELS[lang][2] if i == native else rng.choice(LEVELS[lang][:2])}
            for i, lg in enumerate(chosen)]


def make_profile(rng, fake, lang, hard=False):
    sens = []

    def add(cat, group, value, indirect=False, variant="base"):
        sens.append({"category": cat, "group": group, "value": value, "indirect": indirect,
                     "variant": variant if hard else "base"})
        return value

    male = rng.random() < 0.5
    first = fake.first_name_male() if male else fake.first_name_female()
    last = fake.last_name()
    name = f"{first} {last}"
    city = fake.city()
    age = rng.randint(21, 58)
    birth = date(TODAY.year - age, rng.randint(1, 12), rng.randint(1, 28))
    labeled = rng.random() > 0.3
    l = {**L[lang], **HARD_LABELS[lang]} if hard else L[lang]

    # Persoonsgegevens: willekeurige subset, zoals in echte cv's. De volgorde van de
    # rng-aanroepen ligt vast (kans, dan waarde), zodat dezelfde seed hetzelfde cv geeft.
    fields = [(None, add("name", "identifier", name))]

    def field(label, cat, group, maker, chance=None, variant="base"):
        if chance is not None and rng.random() >= chance:
            return
        fields.append((label, add(cat, group, maker(), variant=variant)))

    field(l["email"], "email", "identifier", lambda: make_email(first, last, rng, fake), variant="other_label")
    field(l["phone"], "phone", "identifier",
          (lambda: hard_phone(rng)) if hard else (lambda: fake.phone_number()), 0.9, "other_format")
    field(l["address"], "address", "identifier",
          (lambda: hard_address(fake, rng, city)) if hard else (lambda: make_address(fake, rng, lang, city)),
          0.8, "other_format")
    field(l["birth"], "birth_date", "discriminatory",
          (lambda: hard_date(birth, lang, rng.randint(0, 2))) if hard else (lambda: fmt_date(birth, lang, rng.randint(0, 2))),
          0.6, "other_format")
    field("Rijksregisternr." if lang == "nl" else "National number", "national_number", "special",
          lambda: rijksregisternummer(birth, rng, male, rng.random() < 0.7), 0.15)
    field(l["nat"], "nationality", "discriminatory", lambda: rng.choice((HARD_NATIONALITY if hard else NATIONALITY)[lang]), 0.4, "unseen_word")
    field(l["marital"], "marital_status", "discriminatory",
          lambda: rng.choice((HARD_MARITAL if hard else MARITAL)[lang]), 0.4, "unseen_word")
    n_kids = rng.choice([0, 0, 1, 2, 3])
    if n_kids and rng.random() < 0.5:
        fields.append((l["children"], add("family", "discriminatory", CHILDREN[lang](n_kids))))

    # Vrije tekst-lekken
    profile = [{"nl": "Gemotiveerde medewerker met oog voor detail en initiatief.",
                "en": "Motivated employee with an eye for detail and initiative."}[lang]]
    extra = []
    if rng.random() < 0.25:
        hh, hc = (HARD_HEALTH, HARD_CONDITIONS) if hard else (HEALTH, CONDITIONS)
        profile.append(add("health", "special", rng.choice(hh[lang]).format(c=rng.choice(hc[lang])),
                           variant="unseen_word"))
    if n_kids > 1 and rng.random() < 0.3:
        fam = HARD_FAMILY[lang][male] if hard else FAMILY[lang].format(w=FAMILY_W[lang][male], n=n_kids)
        profile.append(add("family", "discriminatory", fam, True, "other_phrase"))
    if rng.random() < 0.2:
        extra.append(add("religion", "special", rng.choice((HARD_RELIGION if hard else RELIGION)[lang]).format(city=city),
                         True, "unseen_word"))
    if rng.random() < 0.15:
        extra.append(add("union", "special", (HARD_UNION if hard else UNION)[lang], True, "unseen_word"))
    if rng.random() < 0.08:
        profile.append(add("criminal_record", "special", (HARD_CRIME if hard else CRIME)[lang],
                           variant="other_phrase"))
    if hard and rng.random() < 0.3:   # geboortedatum in lopende tekst
        profile.append(add("birth_date", "discriminatory",
                           HARD_BORN[lang].format(d=hard_date(birth, lang, rng.randint(0, 2)), city=city),
                           variant="other_phrase"))
    if hard and rng.random() < 0.4:   # valstrik: trefwoord, maar niet gevoelig
        extra.append(rng.choice(HARD_TRAPS[lang]))
    extra.append({"nl": "Interesses: fietsen, koken, reizen", "en": "Interests: cycling, cooking, travel"}[lang])

    # Werkervaring (utility): aaneensluitend, van recent naar ouder
    jobs, end = [], date(TODAY.year, TODAY.month, 1)
    for _ in range(rng.randint(1, 3)):
        months = rng.randint(6, 60)
        idx = end.year * 12 + end.month - 1 - months
        start = date(idx // 12, idx % 12 + 1, 1)
        title, tasks = rng.choice(JOBS[lang])
        jobs.append({"title": title, "company": fake.company(), "start": f"{start:%Y-%m}", "end": f"{end:%Y-%m}",
                     "months": months, "tasks": rng.sample(tasks, 2)})
        idx2 = start.year * 12 + start.month - 1 - rng.randint(0, 6)
        end = date(idx2 // 12, idx2 % 12 + 1, 1)

    utility = {"jobs": [{k: j[k] for k in ("title", "company", "start", "end", "months")} for j in jobs],
               "total_months": sum(j["months"] for j in jobs),
               "skills": rng.sample(SKILLS[lang], rng.randint(3, 6)),
               "languages": make_languages(rng, lang),
               "education": rng.sample(EDU[lang], rng.randint(1, 2))}
    return dict(fields=fields, labeled=labeled, profile=" ".join(profile), extra=extra, jobs=jobs,
                utility=utility, sensitive=sens, male=male)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/synthetic")
    ap.add_argument("--hard", action="store_true", help="moeilijke set (cv_data_hard.py)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    for i in range(1, a.n + 1):
        seed = a.seed * 1000 + i
        rng = random.Random(seed)
        lang = "nl" if i % 2 else "en"          # afwisselend NL/EN
        layout = ["single", "table2", "header"][(i // 2) % 3]
        fake = Faker(LOCALES[lang])
        Faker.seed(seed)
        p = make_profile(rng, fake, lang, a.hard)
        stem = f"cv_{i:03d}"
        build_docx(p, lang, layout, out / f"{stem}.docx", rng)
        truth = {"id": stem, "lang": lang, "layout": layout, "labeled": p["labeled"], "seed": seed, "hard": a.hard,
                 "sensitive": p["sensitive"], "utility": p["utility"]}
        (out / f"{stem}.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{a.n} cv's + ground truth geschreven naar {out}")


if __name__ == "__main__":
    main()