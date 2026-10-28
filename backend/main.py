"""
main.py
The MolDeNovo backend server.
It exposes the chemistry engine and the edit library over the web.
"""
from edits import list_edits, apply_edit
from campaign import run_campaign
from campaign import mock_planner
from spark_planner import spark_planner
from fastapi import FastAPI
from fastapi.responses import Response
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import tempfile
from fastapi import UploadFile, File
from meta_client import ask_with_image
from chem_engine import analyze
from edits import list_edits, apply_edit

app = FastAPI(title="MolDeNovo API")

# Lets the website (which will run on a different address) talk to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoleculeRequest(BaseModel):
    smiles: str


class EditRequest(BaseModel):
    smiles: str
    edit_id: str


@app.get("/health")
def health():
    """A simple check that the server is alive."""
    return {"status": "ok"}


@app.get("/edits")
def get_edits():
    """The menu of approved edits."""
    return list_edits()


@app.post("/analyze")
def analyze_molecule(req: MoleculeRequest):
    """Report card for one molecule."""
    return analyze(req.smiles)


@app.post("/apply-edit")
def apply_molecule_edit(req: EditRequest):
    """Apply one approved edit and return every result with its report card."""
    results = []
    for new_smiles in apply_edit(req.smiles, req.edit_id):
        results.append(analyze(new_smiles))
    return {"parent": req.smiles, "edit_id": req.edit_id, "results": results}

class CampaignRequest(BaseModel):
    smiles: str
    max_steps: int = 3
    min_similarity: float = 0.4
    use_spark: bool = True
    protected: list[str] = []


@app.post("/campaign")
def campaign(req: CampaignRequest):
    """Run a full multi-step optimization campaign."""

    def safe_spark(current, tried, rejections):
        try:
            return spark_planner(current, tried, rejections, protected=req.protected)
        except Exception as e:
            print(f"[Spark failed: {e}] -> using mock planner")
            return mock_planner(current, tried, rejections)

    planner = safe_spark if req.use_spark else mock_planner
    return run_campaign(
        req.smiles,
        planner=planner,
        max_steps=req.max_steps,
        min_similarity=req.min_similarity,
        protected=req.protected,
    )

@app.get("/draw")
def draw(smiles: str, width: int = 360, height: int = 260):
    """Return a drawing of a molecule as an SVG image."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return Response(content="Invalid molecule", status_code=400)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().clearBackground = False   # transparent background
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return Response(content=drawer.GetDrawingText(), media_type="image/svg+xml")

READ_PROMPT = """This image shows a chemical structure drawing.
Write the molecule as a SMILES string.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""


@app.post("/read-structure")
def read_structure(file: UploadFile = File(...)):
    """Read a molecule drawing with Muse Wonder, then let RDKit check the answer."""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        return {"valid": False, "error": "Please upload a PNG or JPG image."}

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        text = ask_with_image(READ_PROMPT, path)
    except Exception as e:
        return {"valid": False, "error": f"The vision model call failed: {e}"}
    finally:
        os.remove(path)

    try:
        parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:
        return {"valid": False, "error": "Could not understand the model's reply."}

    guess = parsed.get("smiles", "")
    mol = Chem.MolFromSmiles(guess)
    if mol is None:
        return {
            "valid": False,
            "error": "RDKit rejected what the model read, so it is not a real molecule.",
            "raw_guess": guess,
        }
    return {
        "valid": True,
        "smiles": Chem.MolToSmiles(mol),
        "raw_guess": guess,
        "confidence": parsed.get("confidence", "unknown"),
        "notes": parsed.get("notes", ""),
        "model": "muse-wonder-1.0",
    }