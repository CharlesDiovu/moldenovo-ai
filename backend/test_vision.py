"""
test_vision.py
Ask Muse Wonder to read a molecule drawing, then let RDKit check the answer.
"""

from rdkit import Chem
from meta_client import ask_with_image
from chem_engine import analyze

PROMPT = """This image shows a chemical structure drawing.
Write the molecule as a SMILES string.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""

import json

text = ask_with_image(PROMPT, "test_molecule.png")
print("RAW REPLY:", text)

start, end = text.find("{"), text.rfind("}")
data = json.loads(text[start:end + 1])
guess = data["smiles"]
print("\nWonder's guess:", guess)

mol = Chem.MolFromSmiles(guess)
if mol is None:
    print("RDKit says: NOT a valid molecule. We would reject this.")
else:
    canonical = Chem.MolToSmiles(mol)
    truth = Chem.MolToSmiles(Chem.MolFromSmiles("CC(C)Cc1ccc(cc1)C(C)C(=O)O"))
    print("RDKit says: valid molecule ->", canonical)
    print("Matches ibuprofen:", canonical == truth)
    print("Report card:", analyze(canonical))