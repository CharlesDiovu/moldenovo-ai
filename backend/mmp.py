"""
mmp.py
Matched molecular pair (MMP) evidence from a ChEMBL potency series.
Pure RDKit: no AI model is involved in the statistics.
"""

import os
import csv
import itertools
import statistics
from collections import defaultdict

from rdkit import Chem, RDLogger
from rdkit.Chem import rdMMPA

RDLogger.DisableLog("rdApp.*")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "chembl_series.csv")
STATS = os.path.join(HERE, "data", "mmp_stats.csv")

MAX_VARIABLE_ATOMS = 10    # the changing piece must be small
MAX_VARIANTS_PER_CONTEXT = 60
EFFECT = 0.3               # log units; smaller changes count as noise
H = "[H]"                  # marker for "nothing here, just a hydrogen"


def _heavy(mol):
    return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)


def _canon(smiles):
    """Canonical SMILES for a fragment that contains an attachment point."""
    m = Chem.MolFromSmiles(smiles.replace("[*:1]", "[*]"))
    return Chem.MolToSmiles(m) if m is not None else None


def _clean(smiles):
    """Largest fragment, no stereo, sensible size. None if unusable."""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    m = max(Chem.GetMolFrags(m, asMols=True), key=_heavy)
    if not (8 <= _heavy(m) <= 60):
        return None
    return Chem.MolFromSmiles(Chem.MolToSmiles(m, isomericSmiles=False))


def _fragment_pairs(mol):
    """Single-cut fragmentations -> set of (context, variable)."""
    out = set()
    for tup in rdMMPA.FragmentMol(mol, maxCuts=1, resultsAsMols=False):
        parts = []
        for item in tup:
            if item:
                parts.extend(item.split("."))
        if len(parts) != 2:
            continue
        frags = []
        for p in parts:
            fm = Chem.MolFromSmiles(p.replace("[*:1]", "[*]"))
            if fm is None:
                break
            frags.append((_heavy(fm), Chem.MolToSmiles(fm)))
        if len(frags) != 2:
            continue
        frags.sort()                      # smaller piece first
        (n_var, var), (n_ctx, ctx) = frags
        if n_var <= MAX_VARIABLE_ATOMS and n_var < n_ctx:
            out.add((ctx, var))
    return out


def _hydrogen_pairs(mol):
    """Aromatic C-H sites -> set of (context, '[H]')."""
    out = set()
    for atom in mol.GetAtoms():
        if atom.GetIsAromatic() and atom.GetSymbol() == "C" and atom.GetTotalNumHs() == 1:
            rw = Chem.RWMol(mol)
            d = rw.AddAtom(Chem.Atom(0))
            rw.AddBond(atom.GetIdx(), d, Chem.BondType.SINGLE)
            try:
                Chem.SanitizeMol(rw)
            except Exception:
                continue
            out.add((Chem.MolToSmiles(rw), H))
    return out


def build_stats():
    groups = defaultdict(lambda: defaultdict(list))   # context -> variable -> [pchembl]
    n_mols = 0
    with open(DATA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mol = _clean(row["smiles"])
            if mol is None:
                continue
            try:
                value = float(row["pchembl_value"])
            except ValueError:
                continue
            n_mols += 1
            for ctx, var in _fragment_pairs(mol) | _hydrogen_pairs(mol):
                groups[ctx][var].append(value)

    transforms = defaultdict(list)
    n_contexts_used = 0
    for ctx, variants in groups.items():
        if len(variants) < 2 or len(variants) > MAX_VARIANTS_PER_CONTEXT:
            continue
        n_contexts_used += 1
        med = {v: statistics.median(vals) for v, vals in variants.items()}
        for a, b in itertools.permutations(med, 2):
            transforms[(a, b)].append(med[b] - med[a])

    rows = []
    for (a, b), deltas in transforms.items():
        n = len(deltas)
        rows.append({
            "from": a, "to": b, "n_pairs": n,
            "median_change": round(statistics.median(deltas), 2),
            "pct_improved": round(100 * sum(d >= EFFECT for d in deltas) / n),
            "pct_worse": round(100 * sum(d <= -EFFECT for d in deltas) / n),
        })
    rows.sort(key=lambda r: -r["n_pairs"])

    with open(STATS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows, n_mols, n_contexts_used


# Which of our approved edits have matched-pair evidence.
# (ring C->N and ester->amide need a different method, so they are not covered yet)
EDIT_TRANSFORMS = {
    "aromatic_H_to_F": (H, _canon("[*]F")),
    "aromatic_H_to_OH": (H, _canon("[*]O")),
    "aromatic_H_to_methyl": (H, _canon("[*]C")),
    "chlorine_to_fluorine": (_canon("[*]Cl"), _canon("[*]F")),
    "methyl_to_hydroxymethyl": (_canon("[*]C"), _canon("[*]CO")),
    "acid_to_amide": (_canon("[*]C(=O)O"), _canon("[*]C(N)=O")),
}


def edit_evidence(rows):
    lookup = {(r["from"], r["to"]): r for r in rows}
    return {eid: lookup.get(pair) for eid, pair in EDIT_TRANSFORMS.items()}


if __name__ == "__main__":
    rows, n_mols, n_ctx = build_stats()
    print(f"Molecules used: {n_mols}")
    print(f"Contexts with 2+ variants: {n_ctx}")
    print(f"Distinct transformations: {len(rows)}")

    print("\n=== Evidence for our approved edits ===")
    for eid, r in edit_evidence(rows).items():
        if r is None:
            print(f"{eid:26s} no pairs found")
        else:
            print(f"{eid:26s} n={r['n_pairs']:5d}  median change {r['median_change']:+.2f}  "
                  f"improved {r['pct_improved']}%  worse {r['pct_worse']}%")

    print("\n=== 15 most common transformations ===")
    for r in rows[:15]:
        print(f"{r['from']:>18s} >> {r['to']:<18s} n={r['n_pairs']:5d}  "
              f"median {r['median_change']:+.2f}  improved {r['pct_improved']}%  worse {r['pct_worse']}%")
    print(f"\nSaved {STATS}")