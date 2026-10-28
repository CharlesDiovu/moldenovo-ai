"""
chem_engine.py
The chemistry engine for MolDeNovo.
Takes a molecule (as a SMILES string) and returns a full report card.
Every number comes from RDKit, never from the AI.
"""

from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, QED
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams


def _build_alert_catalog():
    """Build a lookup of known 'problem' substructures (PAINS and Brenk)."""
    params = FilterCatalogParams()
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
    return FilterCatalog(params)


# Built once when the file loads, then reused (it is slow to build).
ALERT_CATALOG = _build_alert_catalog()


def parse_smiles(smiles):
    """Turn a SMILES string into an RDKit molecule. Returns None if invalid."""
    if not smiles or not isinstance(smiles, str):
        return None
    return Chem.MolFromSmiles(smiles.strip())


def analyze(smiles):
    """
    Analyze one molecule. Returns a dictionary (a labeled bundle of results).
    If the SMILES is invalid, 'valid' is False and nothing else is computed.
    """
    mol = parse_smiles(smiles)
    if mol is None:
        return {"valid": False, "smiles": smiles, "error": "Not a valid molecule"}

    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd = rdMolDescriptors.CalcNumHBD(mol)
    hba = rdMolDescriptors.CalcNumHBA(mol)
    rot_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)

    # Lipinski's Rule of 5: list which rules are broken
    lipinski_violations = []
    if mw > 500:
        lipinski_violations.append(f"Molecular weight {mw:.1f} > 500")
    if logp > 5:
        lipinski_violations.append(f"LogP {logp:.2f} > 5")
    if hbd > 5:
        lipinski_violations.append(f"H-bond donors {hbd} > 5")
    if hba > 10:
        lipinski_violations.append(f"H-bond acceptors {hba} > 10")

    # Veber rules (predict oral absorption)
    veber_violations = []
    if rot_bonds > 10:
        veber_violations.append(f"Rotatable bonds {rot_bonds} > 10")
    if tpsa > 140:
        veber_violations.append(f"TPSA {tpsa:.1f} > 140")

    # Structural alerts (warning flags, NOT proof of toxicity)
    alerts = []
    for entry in ALERT_CATALOG.GetMatches(mol):
        alerts.append(entry.GetDescription())

    return {
        "valid": True,
        "smiles": Chem.MolToSmiles(mol),  # standard form of the SMILES
        "mw": round(mw, 2),
        "logp": round(logp, 2),
        "tpsa": round(tpsa, 2),
        "hbd": hbd,
        "hba": hba,
        "rotatable_bonds": rot_bonds,
        "qed": round(QED.qed(mol), 3),
        "lipinski_violations": lipinski_violations,
        "veber_violations": veber_violations,
        "structural_alerts": alerts,
    }


if __name__ == "__main__":
    # This part only runs when you start this file directly (a quick test).
    import json

    test_molecules = {
        "Aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "Caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
        "Not a molecule": "this is nonsense",
    }
    for name, smi in test_molecules.items():
        print(f"\n=== {name} ===")
        print(json.dumps(analyze(smi), indent=2))