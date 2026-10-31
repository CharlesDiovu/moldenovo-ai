# MolDeNovo

**An evidence-grounded medicinal chemistry copilot built on Meta's Muse models.**
Hackathon track: *Push the Frontier* (accelerating a scientific experiment).

Early drug discovery needs tools that small labs can't afford, and AI that
invents chemistry is dangerous in this field. MolDeNovo uses Meta's models to
**plan and read**, and uses RDKit to **apply and verify**. No AI writes a
molecule.

## How Meta's models are used

| Model | Job | Safety net around it |
|---|---|---|
| **SAM 3.1** | Finds every structure in a figure from a paper | Boxes are cropped with a margin and shown to the user |
| **Muse Wonder** | Reads each structure as a SMILES string, twice (low and high reasoning effort) | Two agreeing reads earn a green badge. One read or a disagreement is flagged amber. RDKit rejects invalid molecules. The user confirms next to an RDKit redraw |
| **Muse Spark 1.3** | Chooses the next edit from an approved menu, using your goals and matched-pair statistics | Cannot write SMILES. Its edit is applied by RDKit and checked by guardrails. A failed call falls back to a rule-based planner |
| **Muse Image** | Made the hero artwork on the website | Decoration only. It draws no chemistry |

Everything chemical (properties, edits, validity, drawings, statistics) is computed by RDKit.

## What it does

1. **Read figures.** Upload a figure with many structures. SAM finds them, Wonder reads them, RDKit checks them.
2. **Set the goal.** Pick a profile (oral, brain-penetrant, gut-restricted, custom), protected groups, and how close to stay to your molecule.
3. **Run a campaign.** Spark proposes an edit, RDKit applies it, and guardrails accept or reject it. Every rejection is logged with its reason.
4. **See the evidence.** Each step shows matched-pair statistics beside Spark's rationale. The numbers come from code, not from the model.
5. **Save and share.** Export the whole campaign as a JSON project file and reopen it with no model calls.

## Guardrails (all enforced in code)

- Protected groups cannot be removed.
- Scaffold check: the ring skeleton must be kept, and at most one ring C-to-N swap is allowed.
- Minimum similarity to the starting molecule.
- No new Lipinski, Veber or structural-alert violations.
- Each edit must fix the actual problem against your target profile.
- The campaign stops when the goals are met.

## Measured results

| Test | Result |
|---|---|
| SAM 3.1 on a 5-structure alkaloid figure | 5 of 5 structures found |
| Wonder on 6 computer-drawn molecules, no names shown | 6 of 6 correct (checked by RDKit) |
| Wonder, two reads each, on 5 real alkaloid drawings | 4 agreed on a plausible structure. 1 (strychnine) returned one read only and was flagged |
| Matched-pair evidence, 5-fold cross-validation on 245 held-out EGFR pairs | Direction of potency change: 65% vs 57% for a majority baseline |

The evidence gain comes almost entirely from one edit: adding a hydroxyl (70% vs 30%, n=50). For fluorine, methyl and Cl-to-F, the evidence matched the baseline and added no predictive edge.

## Limits (please read)

- The evidence measures **EGFR potency** (ChEMBL CHEMBL203, 3,806 compounds), not solubility, metabolism or other targets. It will not transfer to unrelated molecules.
- No docking, no trained ADMET models, no synthesis check. The tool optimises developability and evidence-informed design, **not binding**.
- Ring C-to-N and ester-to-amide have no matched-pair evidence. Two other edits have fewer than 30 pairs and are labelled too few to rely on.
- Wonder can misread complex structures, even when RDKit accepts the result. This is why the confirm step exists.
- The scaffold check does not know which ring atoms bind the target.
- The retrospective test holds out whole series, but a molecule can appear in several series, so some leakage remains and the true accuracy is probably lower.
- Spark's statements about which groups are "essential for activity" are its own inference. Only groups the user ticks are enforced.
- Project files store results and settings, not uploaded images.

## Setup (Windows, PowerShell)

Requires Python 3.10+, Node 18+ and a Meta Model API key.

```
git clone https://github.com/CharlesDiovu/moldenovo-ai.git
cd moldenovo-ai\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend\.env` containing one line (never commit it):

```
MODEL_API_KEY=your_key_here
```

Download the evidence data and build the statistics (`backend/data/` is not in the repo):

1. Run `scripts/download_chembl_colab.py` in Google Colab. It saves `chembl_series.csv`.
2. Put the file in `backend\data\`.
3. Run `python mmp.py`, then optionally `python retro_test.py`.

Start the app in two terminals:

```
cd backend ; .\venv\Scripts\Activate.ps1 ; uvicorn main:app --reload
cd frontend ; npm install ; npm run dev
```

Open http://localhost:3000. The hero image is `frontend/public/hero.png`. `python generate_hero.py` makes a new one.

## What was built during the hackathon

All code in this repository was written during the hackathon: the chemistry engine, edit library, campaign loop and guardrails, Spark planner, SAM and Wonder pipelines, matched-pair miner, retrospective test, project save and open, and the website. RDKit, ChEMBL data and the Meta models are third-party. The code was written with AI coding assistance (Claude).

## Data and licences

- Activity data: ChEMBL (CHEMBL203), licensed CC BY-SA 3.0. https://www.ebi.ac.uk/chembl/
- Chemistry: RDKit (BSD).
- Code: MIT.

## Roadmap

Docking against a real pocket, trained ADMET models with applicability-domain flags, evidence for ring swaps and ester-to-amide, a third tie-break read when Wonder's two reads disagree, and a PDF report.
