"""
Vergelijkingstabel voor de thesis: leest de ruwe resultaten van evaluate.py in en
zet de methodes naast elkaar. Dit is de tabel die in het evidence portfolio komt.

Gebruik:
    python compare_experiments.py                                  # alle experiments/exp*.json
    python compare_experiments.py --out experiments/vergelijking.md
"""
import argparse
import json
from pathlib import Path


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n.v.t."


def micro(store):
    ok = sum(v[0] for k, v in store.items() if k != "photo")
    n = sum(v[1] for k, v in store.items() if k != "photo")
    return ok, n


def row(path, r):
    rec_ok, rec_n = micro(r["leak"])
    det_ok, det_n = micro(r["det"])
    g = r["leak_group"]
    ind = r.get("leak_indirect", {})   # oudere runs hebben deze meting nog niet
    direct, indir = ind.get("direct", [0, 0]), ind.get("indirect", [0, 0])
    months = r["months"]
    skill_loss = r["util_orig"]["skill"][0] - r["util_san"]["skill"][0]
    return {
        "methode": r.get("method", path.stem),
        "cv's": r["n_cv"],
        "recall": pct(rec_n - rec_ok, rec_n),
        "special": pct(g["special"][1] - g["special"][0], g["special"][1]) if "special" in g else "n.v.t.",
        "discrim.": pct(g["discriminatory"][1] - g["discriminatory"][0], g["discriminatory"][1]) if "discriminatory" in g else "n.v.t.",
        "identifier": pct(g["identifier"][1] - g["identifier"][0], g["identifier"][1]) if "identifier" in g else "n.v.t.",
        "direct": pct(direct[1] - direct[0], direct[1]),
        "indirect": pct(indir[1] - indir[0], indir[1]),
        "precision": pct(det_ok, det_n),
        "over-redactie": f"{100 * r['over_redaction']:.1f}%",
        "maanden juist": f"{months['exact_san']}/{months['n']}",
        "skills verloren": skill_loss,
        "bestand": path.name,
    }


COLUMNS = ["methode", "cv's", "recall", "special", "discrim.", "identifier", "direct",
           "indirect", "precision", "over-redactie", "maanden juist", "skills verloren", "bestand"]


def markdown(rows):
    head = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in COLUMNS) + "|"
    body = ["| " + " | ".join(str(r[c]) for c in COLUMNS) + " |" for r in rows]
    return "\n".join([head, sep] + body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="experiments/exp*.json")
    ap.add_argument("--out", help="schrijf de markdown-tabel naar dit bestand")
    a = ap.parse_args()
    rows = [row(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(Path(".").glob(a.glob))]
    if not rows:
        raise SystemExit(f"geen resultaten gevonden voor {a.glob}")
    table = markdown(rows)
    print(table)
    if a.out:
        Path(a.out).write_text(table + "\n", encoding="utf-8")
        print(f"\nTabel geschreven naar {a.out}")


if __name__ == "__main__":
    main()
