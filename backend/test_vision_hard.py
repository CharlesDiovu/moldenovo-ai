"""
test_vision_hard.py
Draw 3 lesser-known molecules, ask Muse Wonder to read each, and score it.
"""

import json
import os
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from meta_client import ask_with_image

TESTS = {
    "indole amide": "O=C(Nc1ccc(F)cc1)c1ccc2[nH]ccc2c1",
    "piperazine amide": "CC(C)(C)c1ccc(cc1)C(=O)N1CCN(CC1)c1ncccn1",
    "benzimidazole": "Cc1nc2ccccc2n1CC(=O)NC1CCOCC1",
}

PROMPT = """This image shows a chemical structure drawing.
Write the molecule as a SMILES string.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""

os.makedirs("test_images", exist_ok=True)
score = 0

for name, truth_smiles in TESTS.items():
    # 1. Draw the molecule as a PNG
    mol = Chem.MolFromSmiles(truth_smiles)
    drawer = rdMolDraw2D.MolDraw2DCairo(500, 400)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    path = f"test_images/{name.replace(' ', '_')}.png"
    with open(path, "wb") as f:
        f.write(drawer.GetDrawingText())

    # 2. Ask Wonder to read it
    print(f"\n=== {name} ===")
    try:
        text = ask_with_image(PROMPT, path)
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        print("   Wonder call failed:", e)
        continue

    # 3. Let RDKit judge
    guess = data.get("smiles", "")
    guess_mol = Chem.MolFromSmiles(guess)
    truth = Chem.MolToSmiles(mol)
    if guess_mol is None:
        verdict = "INVALID (RDKit caught it)"
    elif Chem.MolToSmiles(guess_mol) == truth:
        verdict = "CORRECT"
        score += 1
    else:
        verdict = "VALID BUT WRONG MOLECULE"

    print("   truth     :", truth)
    print("   Wonder    :", guess)
    print("   confidence:", data.get("confidence"))
    print("   verdict   :", verdict)

print(f"\nScore: {score} / {len(TESTS)}")