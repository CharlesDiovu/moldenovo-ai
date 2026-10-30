"""
spark_planner.py
The Muse Spark planner: the real "AI" that picks the next edit.
It now also reads matched-pair evidence supplied by code.
"""

from edits import list_edits
from meta_client import ask_json

DEFAULT_PROFILE = {"logp_max": 3.0, "tpsa_max": 100.0}


def _describe(report):
    alerts = ", ".join(report["structural_alerts"]) or "none"
    return (
        f"SMILES {report['smiles']}; MW {report['mw']}; LogP {report['logp']}; "
        f"TPSA {report['tpsa']}; H-bond donors {report['hbd']}; "
        f"H-bond acceptors {report['hba']}; QED {report['qed']}; "
        f"structural alerts: {alerts}"
    )


def spark_planner(current, tried, rejections, protected=None, profile=None, evidence=None):
    """Ask Muse Spark for the next edit. Returns None if no edits are left."""
    menu = {eid: info for eid, info in list_edits().items() if eid not in tried}
    if not menu:
        return None

    evidence = evidence or {}
    lines = []
    for eid, info in menu.items():
        line = f"- {eid}: {info['name']} ({info['why']})"
        if eid in evidence:
            line += f"\n    DATA: {evidence[eid]['summary']}"
        lines.append(line)
    menu_text = "\n".join(lines)

    rejected_text = (
        "\n".join(f"- {r['edit_id']}: {r['reason']}" for r in rejections) or "none yet"
    )
    protected_text = ", ".join(protected) if protected else "none"

    p = profile or DEFAULT_PROFILE
    goal = (
        f"an oral small-molecule drug: keep LogP at or below {p['logp_max']}, "
        f"TPSA at or below {p['tpsa_max']}, add no new structural alerts, "
        "and stay structurally close to the starting molecule"
    )

    prompt = f"""You are a senior medicinal chemist planning one step of a lead optimization.

Project goal: {goal}.

Current molecule: {_describe(current)}
Protected groups (must NOT be removed or altered): {protected_text}

Edits already rejected this round (and why):
{rejected_text}

You may ONLY choose one edit from this menu. Software will apply it and check it.
You cannot write new molecules.
Each edit may have a DATA line: matched molecular pair statistics for EGFR inhibitors
from ChEMBL, measuring how the edit changed POTENCY (pChEMBL, higher is more potent).
{menu_text}

Rules:
- Fix the molecule's most important problem first. If nothing is out of range, pick a modest improvement.
- Do not damage groups likely to be essential for activity. If you are protecting such a group, say so.
- Quote the actual numbers (LogP, TPSA) in your rationale.
- If the chosen edit has a DATA line, cite its numbers exactly as given. Never invent statistics.
- If the DATA says too few pairs, or no evidence, say that plainly.
- The DATA concerns potency in EGFR inhibitors only, not solubility or metabolism, and may not transfer
  if the molecule is not EGFR-like. If an edit more often worsens potency than improves it, weigh that.
- Call your reasoning a hypothesis to test, not a proven improvement.

Reply with JSON only, no other text, in exactly this shape:
{{"edit_id": "<one id from the menu>", "rationale": "<two or three sentences>"}}"""

    reply = ask_json(prompt)
    edit_id = reply.get("edit_id")
    if edit_id not in menu:
        raise ValueError(f"Spark chose an edit that is not available: {edit_id}")
    return {
        "edit_id": edit_id,
        "rationale": str(reply.get("rationale", "")).strip(),
        "planner": "muse-spark-1.3",
    }