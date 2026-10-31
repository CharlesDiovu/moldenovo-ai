"""
retro_test.py
Retrospective test of the matched-pair evidence.
5-fold cross-validation over matched-pair series: statistics are built from
4 folds and used to predict the direction of change in the held-out fold.
Pure RDKit and Python: no AI model is involved.
"""

import os
import csv
import json
import random
import statistics
from collections import defaultdict, Counter

from mmp import (DATA, EFFECT, EDIT_TRANSFORMS, MAX_VARIANTS_PER_CONTEXT,
                 _clean, _fragment_pairs, _hydrogen_pairs)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "retro_results.json")

MIN_PAIRS = 30      # same rule as the app: fewer training pairs -> no prediction
N_FOLDS = 5
SEED = 7


def label(delta):
    if delta >= EFFECT:
        return "improved"
    if delta <= -EFFECT:
        return "worse"
    return "neutral"


def load_groups():
    groups = defaultdict(lambda: defaultdict(list))   # context -> variable -> [values]
    n = 0
    with open(DATA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mol = _clean(row["smiles"])
            if mol is None:
                continue
            try:
                v = float(row["pchembl_value"])
            except ValueError:
                continue
            n += 1
            for ctx, var in _fragment_pairs(mol) | _hydrogen_pairs(mol):
                groups[ctx][var].append(v)
    return groups, n


def majority(items):
    return Counter(items).most_common(1)[0][0] if items else None


def pct(x, n):
    return f"{100 * x / n:.0f}%" if n else "n/a"


def main():
    print("Loading and fragmenting molecules (a minute or two)...")
    groups, n_mols = load_groups()
    usable = [c for c, v in groups.items() if 2 <= len(v) <= MAX_VARIANTS_PER_CONTEXT]
    print(f"Molecules: {n_mols}   usable series (contexts): {len(usable)}")

    rng = random.Random(SEED)
    fold_of = {c: rng.randrange(N_FOLDS) for c in usable}

    # For each covered edit: list of (context, real change) for series containing both variants
    edit_pairs = {}
    for eid, tr in EDIT_TRANSFORMS.items():
        a, b = tr
        if a is None or b is None:
            continue
        lst = []
        for c in usable:
            if a in groups[c] and b in groups[c]:
                d = statistics.median(groups[c][b]) - statistics.median(groups[c][a])
                lst.append((c, d))
        edit_pairs[eid] = lst
    print("\nPairs per edit:", {e: len(l) for e, l in edit_pairs.items()})

    # tallies
    per_edit = defaultdict(lambda: Counter())
    fold_scores = []   # (3-class correct, 3-class total, base correct, dir correct, dir total, dir base correct)

    for k in range(N_FOLDS):
        pooled_train = [d for lst in edit_pairs.values() for c, d in lst if fold_of[c] != k]
        base_class = majority([label(d) for d in pooled_train])
        base_dir = majority([label(d) for d in pooled_train if label(d) != "neutral"])

        t3 = b3 = tot3 = dd = ddb = dtot = 0
        for eid, lst in edit_pairs.items():
            train = [d for c, d in lst if fold_of[c] != k]
            test = [d for c, d in lst if fold_of[c] == k]
            if len(train) < MIN_PAIRS or not test:
                per_edit[eid]["abstained_pairs"] += len(test)
                continue
            counts = Counter(label(d) for d in train)
            pred_class = counts.most_common(1)[0][0]
            pi, pw = counts["improved"], counts["worse"]
            pred_dir = None if pi == pw else ("improved" if pi > pw else "worse")

            for d in test:
                real = label(d)
                tot3 += 1
                t3 += pred_class == real
                b3 += base_class == real
                per_edit[eid]["n3"] += 1
                per_edit[eid]["model3"] += pred_class == real
                per_edit[eid]["base3"] += base_class == real
                if real != "neutral" and pred_dir is not None:
                    dtot += 1
                    dd += pred_dir == real
                    ddb += base_dir == real
                    per_edit[eid]["nd"] += 1
                    per_edit[eid]["modeld"] += pred_dir == real
                    per_edit[eid]["based"] += base_dir == real
        fold_scores.append((t3, b3, tot3, dd, ddb, dtot))

    # ---- report ----
    print("\n=== Per edit (all folds pooled) ===")
    print(f"{'edit':26s} {'tested':>6s} {'3-class model':>14s} {'baseline':>9s}   "
          f"{'non-neutral':>11s} {'direction model':>16s} {'baseline':>9s}")
    for eid in edit_pairs:
        r = per_edit[eid]
        if r["n3"] == 0:
            print(f"{eid:26s} {'-':>6s}  abstained (fewer than {MIN_PAIRS} training pairs "
                  f"or no test pairs)")
            continue
        print(f"{eid:26s} {r['n3']:6d} {pct(r['model3'], r['n3']):>14s} "
              f"{pct(r['base3'], r['n3']):>9s}   {r['nd']:11d} "
              f"{pct(r['modeld'], r['nd']):>16s} {pct(r['based'], r['nd']):>9s}")

    T3 = sum(s[0] for s in fold_scores); B3 = sum(s[1] for s in fold_scores)
    N3 = sum(s[2] for s in fold_scores)
    TD = sum(s[3] for s in fold_scores); BD = sum(s[4] for s in fold_scores)
    ND = sum(s[5] for s in fold_scores)

    print("\n=== Overall ===")
    print(f"3-class   model {pct(T3, N3)} vs baseline {pct(B3, N3)}   (n={N3})")
    print(f"Direction model {pct(TD, ND)} vs baseline {pct(BD, ND)}   (n={ND}, non-neutral pairs)")

    print("\n=== Spread across the 5 folds (direction accuracy, model vs baseline) ===")
    dir_rows = []
    for i, s in enumerate(fold_scores):
        m = 100 * s[3] / s[5] if s[5] else float("nan")
        b = 100 * s[4] / s[5] if s[5] else float("nan")
        dir_rows.append((m, b))
        print(f"fold {i}: model {m:5.1f}%   baseline {b:5.1f}%   (n={s[5]})")
    ms = [m for m, _ in dir_rows if m == m]
    if len(ms) > 1:
        print(f"model mean {statistics.mean(ms):.1f}%  sd {statistics.stdev(ms):.1f}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "folds": N_FOLDS, "seed": SEED, "min_pairs": MIN_PAIRS, "effect_threshold": EFFECT,
            "three_class": {"model": T3, "baseline": B3, "n": N3},
            "direction": {"model": TD, "baseline": BD, "n": ND},
            "per_edit": {e: dict(r) for e, r in per_edit.items()},
        }, f, indent=2)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()