"""
evidence.py
Loads the matched-pair statistics and describes them for each approved edit.
The numbers come from mmp_stats.csv, never from an AI model.
"""

import os
import csv

from edits import list_edits
from mmp import EDIT_TRANSFORMS, STATS

MIN_PAIRS = 30
SERIES = "EGFR inhibitors from ChEMBL (CHEMBL203)"

_cache = None


def _describe(ev):
    if not ev["covered"]:
        return "no matched-pair evidence available for this type of edit"
    if ev["n_pairs"] == 0:
        return "no matched pairs found in the data"
    text = (f"{ev['n_pairs']} matched pairs: median potency change "
            f"{ev['median_change']:+.2f} pChEMBL, improved in {ev['pct_improved']}%, "
            f"worsened in {ev['pct_worse']}%")
    if not ev["enough"]:
        text += f" (only {ev['n_pairs']} pairs, too few to rely on)"
    return text


def load_evidence():
    """Return {edit_id: {covered, n_pairs, ..., enough, summary}}."""
    global _cache
    if _cache is not None:
        return _cache
    lookup = {}
    if os.path.exists(STATS):
        with open(STATS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lookup[(r["from"], r["to"])] = r

    out = {}
    for eid in list_edits():
        if eid not in EDIT_TRANSFORMS:
            ev = {"covered": False, "n_pairs": 0, "enough": False}
        else:
            r = lookup.get(EDIT_TRANSFORMS[eid])
            if r is None:
                ev = {"covered": True, "n_pairs": 0, "enough": False}
            else:
                n = int(r["n_pairs"])
                ev = {
                    "covered": True,
                    "n_pairs": n,
                    "median_change": float(r["median_change"]),
                    "pct_improved": int(r["pct_improved"]),
                    "pct_worse": int(r["pct_worse"]),
                    "enough": n >= MIN_PAIRS,
                }
        ev["summary"] = _describe(ev)
        ev["series"] = SERIES
        out[eid] = ev
    _cache = out
    return out