"""
Evaluatie van een opschoner tegen de ground truth: recall, precision, over-redactie en
verlies aan bruikbare informatie (maanden ervaring, skills, talen, opleiding, functies).
De rapportage staat in eval_report.py.

Gebruik:
  python evaluate.py --data data/synthetic_100 --method regex
  python evaluate.py --data data/synthetic_100 --method ner --out experiments/exp02_ner_100.json
"""
import argparse
import json
import re
from collections import defaultdict
from functools import partial
from pathlib import Path

from eval_report import report
from regex_baseline import docx_has_picture, docx_text

NOW_IDX = 2026 * 12 + 10  # november 2026 = TODAY in de generator
JOB_RX = re.compile(r"\((\d{2})/(\d{4}) - (?:(\d{2})/(\d{4})|heden|present)\)")


def norm(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def spans_of(value, text):
    """Alle posities waar een waarde in de tekst voorkomt (witruimte-onafhankelijk)."""
    pat = r"\s+".join(map(re.escape, value.split()))
    return [(m.start(), m.end()) for m in re.finditer(pat, text, flags=re.I)]


def overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def partial_leak(value, text):
    """Minstens de helft van de tokens van de waarde staat er nog in.

    Zonder deze maatstaf telt een detectie die enkel de gemeente uit een adres haalt als
    'geen lek', omdat de volledige adresstring dan toch verdwenen is.
    """
    toks = [w for w in re.findall(r"\w+", norm(value)) if len(w) > 1]
    return bool(toks) and sum(w in norm(text) for w in toks) / len(toks) >= 0.5


def cleaners(method):
    """(detect, sanitize) voor de gekozen methode: regex, ner of hybrid."""
    if method == "regex":
        from regex_baseline import detect, sanitize
        return detect, sanitize
    from ner_baseline import detect, sanitize
    return partial(detect, method=method), sanitize


def extract_months(text):
    """Totaal aantal maanden ervaring, uit de periodes tussen haakjes na elke functie."""
    total, n = 0, 0
    for m in JOB_RX.finditer(text):
        start = int(m.group(2)) * 12 + int(m.group(1)) - 1
        end = int(m.group(4)) * 12 + int(m.group(3)) - 1 if m.group(3) else NOW_IDX
        total += end - start
        n += 1
    return total if n else None


def utility_scores(text, truth):
    """Per soort (skill, language, education, job) het aandeel feiten dat terug te vinden is."""
    u, t, found = truth["utility"], norm(text), defaultdict(lambda: [0, 0])
    items = ([("skill", s) for s in u["skills"]]
             + [("language", f"{x['lang']} ({x['level']})") for x in u["languages"]]
             + [("education", e) for e in u["education"]]
             + [("job", f"{j['title']} - {j['company']}") for j in u["jobs"]])
    for kind, val in items:
        found[kind][1] += 1
        found[kind][0] += norm(val) in t
    return found, extract_months(text)


def lang_masked(clean, truth):
    """Genormaliseerde opgeschoonde tekst waarin de taalvermeldingen ('Dutch (native)') zijn
    weggehaald. Zo telt de taal 'Nederlands' niet als lek van de nationaliteit 'Nederlands'."""
    t = norm(clean)
    for x in truth["utility"]["languages"]:
        t = t.replace(norm(f"{x['lang']} ({x['level']})"), " ")
    return t


def evaluate(data_dir, show_leaks=False, method="regex"):
    def cnt():
        return defaultdict(lambda: [0, 0])

    leak, leak_group, leak_partial, leak_indirect, det = cnt(), cnt(), cnt(), cnt(), cnt()
    util_orig, util_san = cnt(), cnt()
    chars_removed = chars_wrong = n_cv = 0
    months_ok, months_err = {"orig": 0, "san": 0}, {"orig": 0, "san": 0}
    leaks, detect_fn, sanitize_fn = [], *cleaners(method)

    for jpath in sorted(Path(data_dir).glob("cv_*.json")):
        dpath = jpath.with_suffix(".docx")
        if not dpath.exists():
            print(f"! geen docx bij {jpath.name}, overgeslagen")
            continue
        truth = json.loads(jpath.read_text(encoding="utf-8"))
        text = docx_text(dpath)
        dets = detect_fn(text)
        clean = sanitize_fn(text, dets)
        clean_chk = lang_masked(clean, truth)  # lekcontrole zonder de talensectie
        has_pic = docx_has_picture(dpath)
        n_cv += 1
        gt_spans = []  # (start, einde, categorie)

        # 1. recall / lekmeting, 1b. gedeeltelijk lek en direct vs. indirect
        for item in truth["sensitive"]:
            cat, val, grp = item["category"], item["value"], item["group"]
            if cat == "photo":
                if has_pic is None:
                    continue  # niet te meten op een tekstexport
                # een tekstgebaseerde opschoner kan geen foto verwijderen: enkel apart
                # bijhouden, niet in de groepstotalen (anders verdrinkt 'special' erin)
                leak[cat][1] += 1; leak[cat][0] += 1
                continue
            leaked = norm(val) in clean_chk
            leak[cat][1] += 1; leak[cat][0] += leaked
            leak_group[grp][1] += 1; leak_group[grp][0] += leaked
            gt_spans += [(*sp, cat) for sp in spans_of(val, text)]
            if leaked:
                leaks.append((truth["id"], cat, val))
            leak_partial[cat][1] += 1
            leak_partial[cat][0] += partial_leak(val, clean_chk)
            kind = "indirect" if item.get("indirect") else "direct"
            leak_indirect[kind][1] += 1; leak_indirect[kind][0] += leaked

        # 2. precision
        for s, e, cat, _ in dets:
            if cat == "name":
                continue  # titel-heuristiek, apart rapporteren is niet zinvol
            det[cat][1] += 1
            det[cat][0] += any(overlap((s, e), (a, b)) and c == cat for a, b, c in gt_spans)
            chars_removed += e - s
            if not any(overlap((s, e), (a, b)) for a, b, _ in gt_spans):
                chars_wrong += e - s

        # 3. verlies aan bruikbare informatie
        for label, txt, store in (("orig", text, util_orig), ("san", clean, util_san)):
            found, months = utility_scores(txt, truth)
            for k, (f, t) in found.items():
                store[k][0] += f; store[k][1] += t
            gt = truth["utility"]["total_months"]
            months_ok[label] += months == gt
            months_err[label] += abs((months or 0) - gt)

    res = {"n_cv": n_cv, "method": method, "leak": leak, "leak_group": leak_group,
           "leak_partial": leak_partial, "leak_indirect": leak_indirect, "det": det,
           "over_redaction": chars_wrong / chars_removed if chars_removed else 0.0,
           "util_orig": util_orig, "util_san": util_san,
           "months": {"n": n_cv, "exact_orig": months_ok["orig"], "exact_san": months_ok["san"],
                      "mae_orig": months_err["orig"] / max(n_cv, 1),
                      "mae_san": months_err["san"] / max(n_cv, 1)}}
    if show_leaks:
        print("\nLekken (cv, categorie, waarde):")
        for row in leaks:
            print("  ", row)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic")
    ap.add_argument("--show-leaks", action="store_true")
    ap.add_argument("--method", default="regex", choices=("regex", "ner", "hybrid"))
    ap.add_argument("--out", help="schrijf ruwe resultaten naar JSON")
    a = ap.parse_args()
    r = evaluate(a.data, a.show_leaks, a.method)
    report(r)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResultaten geschreven naar {a.out}")


if __name__ == "__main__":
    main()