"""
make_test_figure.py
Draws 6 lesser-known molecules in one figure, with NO name labels.
Saves the true answers so we can grade Wonder fairly.
"""
import json
from rdkit import Chem
from rdkit.Chem import Draw

TRUTHS = [
    "CC(C)Oc1ccc(cc1)C(=O)NCc1ccncc1",
    "COc1cc2c(cc1OC)CCN(C2)C(=O)c1ccco1",
    "Cc1cc(nn1C)C(=O)N1CCC(CC1)c1ccccc1",
    "O=C(O)c1ccc(cc1)S(=O)(=O)N1CCOCC1",
    "CCn1cc(c2ccccc21)C(=O)NC1CC1",
    "Nc1ncnc2[nH]ccc12",
]
mols = [Chem.MolFromSmiles(s) for s in TRUTHS]
img = Draw.MolsToGridImage(mols, molsPerRow=3, subImgSize=(320, 260))
img.save("test_figure2.png")
with open("truths.json", "w") as f:
    json.dump([Chem.MolToSmiles(m) for m in mols], f)
print("Saved test_figure2.png and truths.json")