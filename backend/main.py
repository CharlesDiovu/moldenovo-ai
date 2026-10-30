"""
main.py
The MolDeNovo backend server.
It exposes the chemistry engine, the campaign loop, and the Meta-model pipelines.
"""

import io
import os
import json
import base64
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from chem_engine import analyze
from edits import list_edits, apply_edit
from campaign import run_campaign, mock_planner, PROTECTED_GROUPS
from spark_planner import spark_planner
from evidence import load_evidence
from meta_client import ask_with_image
from sam_client import find_structures, crop_structures

app = FastAPI(title="MolDeNovo API")

# Lets the website (which runs on a different address) talk to this server.
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


class CampaignRequest(BaseModel):
    smiles: str
    max_steps: int = 3
    min_similarity: float = 0.4
    use_spark: bool = True
    protected: list[str] = []
    logp_max: float = 3.0
    tpsa_max: float = 100.0
    stop_when_met: bool = True


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


@app.post("/campaign")
def campaign(req: CampaignRequest):
    """Run a full multi-step optimization campaign."""
    profile = {"logp_max": req.logp_max, "tpsa_max": req.tpsa_max}
    evidence = load_evidence()

    def safe_spark(current, tried, rejections):
        try:
            return spark_planner(current, tried, rejections,
                                 protected=req.protected, profile=profile,
                                 evidence=evidence)
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
        profile=profile,
        stop_when_met=req.stop_when_met,
        evidence=evidence,
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


@app.get("/groups")
def groups(smiles: str):
    """Which protectable groups does this molecule actually contain?"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"groups": []}
    found = []
    for name, smarts in PROTECTED_GROUPS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if mol.HasSubstructMatch(pattern):
            found.append(name)
    return {"groups": found}


# ---------------------------------------------------------------
# Single drawing -> SMILES (Muse Wonder, checked by RDKit)
# ---------------------------------------------------------------
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


# ---------------------------------------------------------------
# Whole figure -> many structures (SAM 3.1 + Muse Wonder + RDKit)
# ---------------------------------------------------------------
FIGURE_PROMPT = """This image shows one chemical structure drawing.
Read ONLY the drawn atoms and bonds. Ignore any printed name.
Write the molecule as a SMILES string. Give every ring its own digit (1, 2, 3, 4...) and never reuse a ring digit.
Reply with JSON only, in exactly this shape:
{"smiles": "<SMILES>", "confidence": "high|medium|low", "notes": "<anything unclear>"}"""

MAX_STRUCTURES = 12


def _attempt(path, effort):
    """One read of one crop. Never raises; failures are reported in the result."""
    try:
        text = ask_with_image(FIGURE_PROMPT, path, effort=effort)
        parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        return {"effort": effort, "smiles": None, "raw": "", "confidence": "unknown",
                "notes": "", "error": str(e)[:200]}
    raw = parsed.get("smiles", "")
    mol = Chem.MolFromSmiles(raw)
    return {
        "effort": effort,
        "smiles": Chem.MolToSmiles(mol) if mol is not None else None,
        "raw": raw,
        "confidence": parsed.get("confidence", "unknown"),
        "notes": parsed.get("notes", ""),
        "error": None if mol is not None else "RDKit rejected this read",
    }


def _read_crop(index_and_image):
    index, img = index_and_image
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img.save(tmp, format="PNG")
        path = tmp.name
    try:
        reads = [_attempt(path, "low"), _attempt(path, "high")]
    finally:
        os.remove(path)

    good = [r for r in reads if r["smiles"]]
    if len(good) == 2 and good[0]["smiles"] == good[1]["smiles"]:
        status, chosen = "agreed", good[1]
    elif len(good) == 2:
        status, chosen = "disagree", good[1]   # high-effort read, but flagged
    elif len(good) == 1:
        status, chosen = "single", good[0]
    else:
        status, chosen = "failed", None

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {
        "index": index,
        "crop_png": base64.b64encode(buf.getvalue()).decode("ascii"),
        "status": status,
        "valid": chosen is not None,
        "smiles": chosen["smiles"] if chosen else None,
        "confidence": chosen["confidence"] if chosen else "unknown",
        "notes": chosen["notes"] if chosen else "",
        "reads": [{"effort": r["effort"], "smiles": r["smiles"],
                   "confidence": r["confidence"], "error": r["error"]} for r in reads],
    }


@app.post("/read-figure")
def read_figure(file: UploadFile = File(...)):
    """SAM finds the structures, Wonder reads each, RDKit checks each."""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        return {"error": "Please upload a PNG or JPG image."}

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        boxes = find_structures(path)
        total_found = len(boxes)
        boxes = boxes[:MAX_STRUCTURES]
        crops = crop_structures(path, boxes)
    except Exception as e:
        return {"error": f"Segmentation failed: {e}"}
    finally:
        os.remove(path)

    if not crops:
        return {"error": "SAM found no structures in this image.", "found": 0}

    with ThreadPoolExecutor(max_workers=3) as pool:
        cards = list(pool.map(_read_crop, enumerate(crops)))

    return {
        "found": total_found,
        "read": len(cards),
        "valid": sum(1 for c in cards if c["valid"]),
        "capped": total_found > MAX_STRUCTURES,
        "models": {"segmentation": "sam-3.1", "reading": "muse-wonder-1.0"},
        "cards": cards,
    }