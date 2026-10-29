"""
test_read_fair.py
Wonder reads each crop. RDKit compares the answer with the true molecules.
Order-independent: we just check whether each answer matches any truth.
"""
import glob, json
from rdkit import Chem
from meta_client import ask_with_image

PROMPT = """This image shows one chemical structure drawing.
Read ONLY the drawn atoms and bonds. Ignore any printed name.
Write the molecule as a SMILES string.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""

truths = json.load(open("truths.json"))
found = set()
paths = sorted(glob.glob("crops/crop_*.png"))
print(f"{len(paths)} crops, {len(truths)} true molecules\n")

for path in paths:
    print("===", path)
    try:
        text = ask_with_image(PROMPT, path)
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        print("   call failed:", e)
        continue
    mol = Chem.MolFromSmiles(data.get("smiles", ""))
    if mol is None:
        print("   INVALID (RDKit caught it), confidence:", data.get("confidence"))
        continue
    can = Chem.MolToSmiles(mol)
    if can in truths:
        found.add(can)
        print("   CORRECT, matches true molecule", truths.index(can) + 1,
              "| confidence:", data.get("confidence"))
    else:
        print("   VALID BUT WRONG:", can, "| confidence:", data.get("confidence"))

print(f"\nCorrectly read: {len(found)} / {len(truths)}")