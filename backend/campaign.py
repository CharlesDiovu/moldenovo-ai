"""
campaign.py
The optimization loop for MolDeNovo.
Planner proposes -> RDKit applies -> guardrails check -> accept or reject -> repeat.
Stops early once the target profile is met.
"""

from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator

from chem_engine import analyze
from edits import list_edits, apply_edit

_fp_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

# Groups a chemist can mark as "do not touch" (SMARTS patterns).
PROTECTED_GROUPS = {
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "ester": "[#6][CX3](=O)[OX2][#6]",
    "primary_amide": "[CX3](=O)[NX3H2]",
}

# The chemist's target profile. The website can change these numbers.
DEFAULT_PROFILE = {"logp_max": 3.0, "tpsa_max": 100.0}


def similarity(smiles_a, smiles_b):
    """Tanimoto similarity: 1.0 = identical, 0.0 = nothing in common."""
    a, b = Chem.MolFromSmiles(smiles_a), Chem.MolFromSmiles(smiles_b)
    if a is None or b is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(_fp_gen.GetFingerprint(a), _fp_gen.GetFingerprint(b))


def lost_protected_group(candidate_smiles, start_smiles, protected):
    """Return the name of a protected group the candidate has lost, else None."""
    if not protected:
        return None
    cand = Chem.MolFromSmiles(candidate_smiles)
    start = Chem.MolFromSmiles(start_smiles)
    for name in protected:
        smarts = PROTECTED_GROUPS.get(name)
        if smarts is None:
            continue
        pattern = Chem.MolFromSmarts(smarts)
        if len(cand.GetSubstructMatches(pattern)) < len(start.GetSubstructMatches(pattern)):
            return name
    return None


def goals_met(report, profile=None):
    """True when the molecule already satisfies the target profile."""
    p = profile or DEFAULT_PROFILE
    return (
        report["logp"] <= p["logp_max"]
        and report["tpsa"] <= p["tpsa_max"]
        and not report["lipinski_violations"]
        and not report["veber_violations"]
    )


def is_improvement(candidate, current, profile=None):
    """An edit only counts if it fixes the molecule's actual problem."""
    p = profile or DEFAULT_PROFILE
    if current["logp"] > p["logp_max"]:      # problem: too oily -> LogP must drop
        return candidate["logp"] < current["logp"] - 0.1 and candidate["qed"] >= current["qed"] - 0.02
    if current["tpsa"] > p["tpsa_max"]:      # problem: too polar -> TPSA must drop
        return candidate["tpsa"] < current["tpsa"] - 5 and candidate["qed"] >= current["qed"] - 0.02
    return candidate["qed"] > current["qed"] + 0.01   # otherwise: a real QED gain


def check_guardrails(candidate, current, start_smiles, min_similarity, protected=None, profile=None):
    """Return a reason string if the candidate must be rejected, else None."""
    if not candidate["valid"]:
        return "Not a valid molecule"
    lost = lost_protected_group(candidate["smiles"], start_smiles, protected)
    if lost:
        return f"Damages protected group: {lost}"
    if len(candidate["lipinski_violations"]) > len(current["lipinski_violations"]):
        return "Breaks Lipinski: " + "; ".join(candidate["lipinski_violations"])
    if len(candidate["veber_violations"]) > len(current["veber_violations"]):
        return "Breaks Veber: " + "; ".join(candidate["veber_violations"])
    if len(candidate["structural_alerts"]) > len(current["structural_alerts"]):
        return "Adds structural alert(s): " + ", ".join(candidate["structural_alerts"])
    sim = similarity(candidate["smiles"], start_smiles)
    if sim < min_similarity:
        return f"Too different from the starting molecule (similarity {sim:.2f} < {min_similarity})"
    if not is_improvement(candidate, current, profile):
        return (f"Doesn't fix the problem (LogP {candidate['logp']} vs {current['logp']}, "
                f"QED {candidate['qed']} vs {current['qed']})")
    return None


# ---------------------------------------------------------------
# THE MOCK PLANNER (the fallback if Muse Spark is unavailable).
# It keeps fixed thresholds, because it is only a safety net.
# ---------------------------------------------------------------
def mock_planner(current, tried, rejections):
    menu = list_edits()
    if current["logp"] > 3:
        priority = ["aromatic_CH_to_N", "aromatic_H_to_OH", "methyl_to_hydroxymethyl",
                    "acid_to_amide", "ester_to_amide"]
        problem = f"LogP is {current['logp']} (above 3), so the molecule is quite oily"
    elif current["tpsa"] > 100:
        priority = ["acid_to_amide", "aromatic_H_to_F", "aromatic_H_to_methyl"]
        problem = f"TPSA is {current['tpsa']} (above 100), which can limit membrane crossing"
    else:
        priority = ["aromatic_H_to_F", "ester_to_amide", "aromatic_CH_to_N",
                    "aromatic_H_to_OH", "methyl_to_hydroxymethyl", "acid_to_amide"]
        problem = "Properties are in range, so I'll look for gains in stability and drug-likeness"

    if current["logp"] > 3 or current["tpsa"] > 100:
        order = priority            # stay focused on the real problem
    else:
        order = priority + [e for e in menu if e not in priority]

    for edit_id in order:
        if edit_id in tried:
            continue
        note = ""
        if rejections:
            note = f" My last idea was rejected ({rejections[-1]['reason']}), so I'm trying something different."
        return {
            "edit_id": edit_id,
            "rationale": f"{problem}. Trying '{menu[edit_id]['name']}': {menu[edit_id]['why']}{note}",
        }
    return None


def run_campaign(start_smiles, planner=mock_planner, max_steps=5, min_similarity=0.4,
                 protected=None, profile=None, stop_when_met=True):
    """Run a multi-step optimization campaign and return the full story."""
    start = analyze(start_smiles)
    if not start["valid"]:
        return {"error": "Starting molecule is not valid"}

    p = profile or DEFAULT_PROFILE
    menu = list_edits()
    current = start
    steps, rejections = [], []
    stop_reason = f"Reached the maximum of {max_steps} steps"

    for step_number in range(1, max_steps + 1):
        # Stop rule: do not keep editing a molecule that already meets the goals.
        if stop_when_met and goals_met(current, p):
            if steps:
                stop_reason = (f"Goals met: LogP {current['logp']} (limit {p['logp_max']}), "
                               f"TPSA {current['tpsa']} (limit {p['tpsa_max']}). Stopped on purpose.")
            else:
                stop_reason = (f"The starting molecule already meets the target profile "
                               f"(LogP {current['logp']} / limit {p['logp_max']}, "
                               f"TPSA {current['tpsa']} / limit {p['tpsa_max']}). "
                               "Untick 'Stop when goals are met' to explore polish edits.")
            break

        tried, step_rejections, accepted = set(), [], False

        while True:
            proposal = planner(current, tried, step_rejections)
            if proposal is None:
                break
            edit_id = proposal["edit_id"]
            tried.add(edit_id)

            candidates = apply_edit(current["smiles"], edit_id)
            if not candidates:
                rej = {"step": step_number, "edit_id": edit_id,
                       "rationale": proposal["rationale"],
                       "reason": "Edit does not fit this molecule"}
                step_rejections.append(rej)
                rejections.append(rej)
                continue

            # Score every candidate; keep the best one that passes all guardrails.
            best, best_reason = None, None
            for smi in candidates:
                cand = analyze(smi)
                reason = check_guardrails(cand, current, start["smiles"],
                                          min_similarity, protected, profile)
                if reason is None:
                    if best is None or cand["qed"] > best["qed"]:
                        best = cand
                else:
                    best_reason = reason

            if best is None:
                rej = {"step": step_number, "edit_id": edit_id,
                       "rationale": proposal["rationale"], "reason": best_reason}
                step_rejections.append(rej)
                rejections.append(rej)
                continue

            steps.append({
                "step": step_number,
                "edit_id": edit_id,
                "edit_name": menu[edit_id]["name"],
                "rationale": proposal["rationale"],
                "planner": proposal.get("planner", "mock"),
                "before": current,
                "after": best,
                "qed_change": round(best["qed"] - current["qed"], 3),
                "similarity_to_start": round(similarity(best["smiles"], start["smiles"]), 2),
            })
            current = best
            accepted = True
            break

        if not accepted:
            stop_reason = "No remaining edit passes the guardrails"
            break

    return {"start": start, "steps": steps, "rejections": rejections,
            "final": current, "stop_reason": stop_reason,
            "goals_met": goals_met(current, p)}


if __name__ == "__main__":
    r = run_campaign("CC(C)Cc1ccc(cc1)C(C)C(=O)O", min_similarity=0.7,
                     protected=["carboxylic_acid"])
    print("steps:", len(r["steps"]))
    print("stopped:", r["stop_reason"])