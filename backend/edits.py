"""
edits.py
The approved edit library for MolDeNovo.
The AI picks an edit by its ID. RDKit performs it.
The AI never writes a molecule itself.
"""

from rdkit import Chem
from rdkit.Chem import AllChem

# Each edit: a readable name, the recipe (reaction SMARTS), and why a chemist does it.
EDIT_LIBRARY = {
    "aromatic_H_to_F": {
        "name": "Add fluorine to a ring",
        "smarts": "[cH:1]>>[c:1]F",
        "why": "Blocks metabolic hot spots and fine-tunes lipophilicity.",
    },
    "aromatic_H_to_OH": {
        "name": "Add hydroxyl to a ring",
        "smarts": "[cH:1]>>[c:1]O",
        "why": "Adds polarity to improve solubility (can add metabolic liability).",
    },
    "aromatic_H_to_methyl": {
        "name": "Add methyl to a ring",
        "smarts": "[cH:1]>>[c:1]C",
        "why": "Adds lipophilicity and can fill a small pocket.",
    },
    "aromatic_CH_to_N": {
        "name": "Swap a ring carbon for nitrogen",
        "smarts": "[c;H1:1]>>[n:1]",
        "why": "Lowers LogP and adds a hydrogen-bond acceptor (benzene to pyridine).",
    },
    "methyl_to_hydroxymethyl": {
        "name": "Methyl to hydroxymethyl",
        "smarts": "[c:1][CH3:2]>>[c:1][CH2:2]O",
        "why": "Adds a polar handle to lower LogP.",
    },
    "chlorine_to_fluorine": {
        "name": "Chlorine to fluorine",
        "smarts": "[c:1][Cl]>>[c:1]F",
        "why": "Reduces size and lipophilicity.",
    },
    "ester_to_amide": {
        "name": "Ester to amide",
        "smarts": "[#6:1][C:2](=[O:3])[O;X2:4][#6:5]>>[#6:1][C:2](=[O:3])[N:4][#6:5]",
        "why": "Amides are usually more stable in the body than esters.",
    },
    "acid_to_amide": {
        "name": "Carboxylic acid to primary amide",
        "smarts": "[C:1](=[O:2])[OX2H1]>>[C:1](=[O:2])N",
        "why": "Removes the acid charge, which can improve membrane crossing.",
    },
}

# Convert every recipe into a ready-to-use reaction once, when the file loads.
_REACTIONS = {
    edit_id: AllChem.ReactionFromSmarts(info["smarts"])
    for edit_id, info in EDIT_LIBRARY.items()
}


def list_edits():
    """Return the menu of edits (this is what the AI will be shown)."""
    return {eid: {"name": i["name"], "why": i["why"]} for eid, i in EDIT_LIBRARY.items()}


def apply_edit(smiles, edit_id):
    """
    Apply one edit at every place it fits on the molecule.
    Returns a list of new, valid, unique SMILES (empty if the edit doesn't fit).
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or edit_id not in _REACTIONS:
        return []

    parent = Chem.MolToSmiles(mol)
    seen = set()
    results = []

    for products in _REACTIONS[edit_id].RunReactants((mol,)):
        for product in products:
            try:
                Chem.SanitizeMol(product)           # chemistry validity check
                new_smiles = Chem.MolToSmiles(product)
                if Chem.MolFromSmiles(new_smiles) is None:
                    continue
            except Exception:
                continue                             # impossible molecule: discard
            if new_smiles == parent or new_smiles in seen:
                continue
            seen.add(new_smiles)
            results.append(new_smiles)
    return results


if __name__ == "__main__":
    # Quick test: try every edit on two molecules and show what changes.
    from chem_engine import analyze

    for label, smi in [("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
                       ("p-Toluic acid", "Cc1ccc(cc1)C(=O)O")]:
        base = analyze(smi)
        print(f"\n######## {label}  (MW {base['mw']}, LogP {base['logp']}) ########")
        for edit_id, info in EDIT_LIBRARY.items():
            options = apply_edit(smi, edit_id)
            print(f"\n{info['name']}: {len(options)} possible result(s)")
            for new_smi in options[:2]:
                new = analyze(new_smi)
                d_logp = new["logp"] - base["logp"]
                d_mw = new["mw"] - base["mw"]
                print(f"   {new_smi}   LogP change {d_logp:+.2f}, MW change {d_mw:+.2f}")