"""
test_read_crops.py
Muse Wonder reads each SAM crop. RDKit checks every answer.
As an extra check, we compare each molecular formula with the known
formula of the molecule the figure labels (these are well-known alkaloids).
"""

import glob
import json
import re
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from meta_client import ask_with_image

# Box number -> (name from the figure's label, known formula)
EXPECTED = {
    0: ("nicotine", "C10H14N2"),
    1: ("ephedrine", "C10H15NO"),
    2: ("morphine", "C17H19NO3"),
    3: ("quinine", "C20H24N2O2"),
    4: ("strychnine", "C21H22N2O2"),
}

PROMPT = """This image shows one chemical structure drawing.
Write the molecule as a SMILES string.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""

paths = sorted(glob.glob("crops/crop_*.png"),
               key=lambda p: int(re.search(r"(\d+)", p.split("crop_")[-1]).group(1)))
matches = 0

for path in paths:
    idx = int(re.search(r"crop_(\d+)", path).group(1))
    name, formula = EXPECTED.get(idx, ("unknown", None))
    print(f"\n=== crop {idx} (figure label: {name}) ===")
    try:
        text = ask_with_image(PROMPT, path)
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        print("   Wonder call failed:", e)
        continue

    guess = data.get("smiles", "")
    mol = Chem.MolFromSmiles(guess)
    print("   Wonder says :", guess)
    print("   confidence  :", data.get("confidence"), "|", data.get("notes", ""))
    if mol is None:
        print("   RDKit       : INVALID (caught)")
        continue
    got = rdMolDescriptors.CalcMolFormula(mol)
    ok = (got == formula)
    matches += ok
    print(f"   RDKit       : valid, formula {got}  (expected {formula})  ->",
          "FORMULA MATCHES" if ok else "FORMULA DIFFERS")

print(f"\nFormula matches: {matches} / {len(paths)}")