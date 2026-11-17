"""Rapportage van een evaluatierun: de tabellen die je in de thesis en de verdediging gebruikt."""
GROUPS = ("special", "discriminatory", "identifier")


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "   n.v.t."


def dump(title, cols, rows, label_w=18):
    """Kopieerbaar tekstblok: titel, kolomkoppen (naam, breedte) en rijen."""
    print(f"\n{title}")
    print(f"{cols[0][0]:{label_w}}" + "".join(f"{h:>{w}}" for h, w in cols[1:]))
    for label, *vals in rows:
        print(f"{label:{label_w}}" + "".join(f"{v:>{w}}" for v, (_, w) in zip(vals, cols[1:])))


def report(r):
    print(f"\nMethode: {r.get('method', 'regex')}  |  {r['n_cv']} cv's geëvalueerd")
    print("Foto's staan niet in deze tabellen: een tekstpijplijn kan ze niet verwijderen.")

    rows = [(c, r["leak_partial"][c][1], pct(r["leak"][c][1] - r["leak"][c][0], r["leak"][c][1]),
             pct(r["leak_partial"][c][1] - r["leak_partial"][c][0], r["leak_partial"][c][1]))
            for c in sorted(r["leak_partial"])]
    tn, tl = sum(v[1] for v in r["leak_partial"].values()), sum(v[0] for v in r["leak_partial"].values())
    ts = sum(r["leak"][c][0] for c in r["leak_partial"])
    rows.append(("TOTAAL (micro)", tn, pct(tn - ts, tn), pct(tn - tl, tn)))
    dump("RECALL per categorie: streng (volledige waarde weg) vs. gedeeltelijk (deel weg)",
         [("categorie", 0), ("n", 5), ("streng", 9), ("gedeelt.", 10)], rows)

    rows = [(g, *r["leak_group"][g][::-1],
             pct(r["leak_group"][g][1] - r["leak_group"][g][0], r["leak_group"][g][1]))
            for g in GROUPS if g in r["leak_group"]]
    rows += [("  " + g, *r["leak_indirect"][g][::-1],
              pct(r["leak_indirect"][g][1] - r["leak_indirect"][g][0], r["leak_indirect"][g][1]))
             for g in ("direct", "indirect") if g in r["leak_indirect"]]
    dump("RECALL per groep, en naar aard van het lek (direct / indirect)",
         [("groep / aard", 0), ("n", 5), ("gelekt", 8), ("recall", 9)], rows)

    dump("PRECISION per categorie (detecties die een echte gevoelige waarde raken)",
         [("categorie", 0), ("detecties", 10), ("juist", 7), ("precision", 11)],
         [(c, n, ok, pct(ok, n)) for c, (ok, n) in sorted(r["det"].items())])
    print(f"\nOver-redactie (weggehaalde tekens die niet gevoelig waren): {100 * r['over_redaction']:.1f}%")

    dump("BRUIKBARE INFORMATIE (aandeel feiten dat in de tekst terug te vinden is)",
         [("soort", 0), ("origineel", 11), ("opgeschoond", 13), ("verlies", 9)],
         [(k, pct(*r["util_orig"][k]), pct(*r["util_san"][k]),
           f"{100 * (r['util_orig'][k][0] - r['util_san'][k][0]) / r['util_orig'][k][1]:8.1f}pt")
          for k in ("job", "skill", "language", "education") if r["util_orig"][k][1]], label_w=12)
    m = r["months"]
    print(f"\nErvaring in maanden: exact juist {m['exact_orig']}/{m['n']} (origineel), "
          f"{m['exact_san']}/{m['n']} (opgeschoond); gem. fout {m['mae_orig']:.1f} / {m['mae_san']:.1f} maanden")
