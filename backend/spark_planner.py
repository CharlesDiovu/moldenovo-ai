"""
spark_planner.py
The Muse Spark planner: the real "AI" that picks the next edit.
Same inputs and outputs as the mock planner.
"""

from edits import list_edits
from meta_client import ask_json

PROJECT_GOAL = (
    "an oral small-molecule drug: keep LogP between 1 and 3, TPSA under 100, "
    "add no new structural alerts, and stay structurally close to the starting molecule"
)


def _describe(report):
    alerts = ", ".join(report["structural_alerts"]) or "none"
    return (
        f"SMILES {report['smiles']}; MW {report['mw']}; LogP {report['logp']}; "
        f"TPSA {report['tpsa']}; H-bond donors {report['hbd']}; "
        f"H-bond acceptors {report['hba']}; QED {report['qed']}; "
        f"structural alerts: {alerts}"
    )


def spark_planner(current, tried, rejections, protected=None):
    """Ask Muse Spark for the next edit. Returns None if no edits are left."""
    menu = {eid: info for eid, info in list_edits().items() if eid not in tried}
    if not menu:
        return None

    menu_text = "\n".join(
        f"- {eid}: {info['name']} ({info['why']})" for eid, info in menu.items()
    )
    rejected_text = (
        "\n".join(f"- {r['edit_id']}: {r['reason']}" for r in rejections) or "none yet"
    )
    protected_text = ", ".join(protected) if protected else "none"
    prompt = f"""You are a senior medicinal chemist planning one step of a lead optimization.

Project goal: {PROJECT_GOAL}.

Current molecule: {_describe(current)}
Protected groups (must NOT be removed or altered): {protected_text}
Edits already rejected this round (and why):
{rejected_text}

You may ONLY choose one edit from this menu. Software will apply it and check it.
You cannot write new molecules.
{menu_text}

Rules:
- Fix the molecule's most important problem first. If nothing is out of range, pick a modest improvement.
- Do not damage groups likely to be essential for activity (for example the carboxylic acid in an NSAID). If you are protecting such a group, say so.
- Call your reasoning a hypothesis to test, not a proven improvement.

Reply with JSON only, no other text, in exactly this shape:
{{"edit_id": "<one id from the menu>", "rationale": "<two sentences>"}}"""

    reply = ask_json(prompt)
    edit_id = reply.get("edit_id")
    if edit_id not in menu:
        raise ValueError(f"Spark chose an edit that is not available: {edit_id}")
    return {
        "edit_id": edit_id,
        "rationale": str(reply.get("rationale", "")).strip(),
        "planner": "muse-spark-1.3",
    }