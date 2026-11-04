# MolDeNovo

**An evidence-grounded medicinal chemistry copilot built on Meta's Muse models.**

### Try it now: https://moldenovo-ai.vercel.app/

No install needed. Hackathon track: *Push the Frontier* (accelerating a scientific experiment).
Demo video: *(https://youtu.be/mp_2YTwgDoI?si=xcV2IKFWnWxaPL89)*

> The first request after a quiet period can take up to a minute while the server wakes up. A campaign takes about a minute to run.

Early drug discovery needs tools that small labs can't afford, and AI that invents chemistry is dangerous in this field. MolDeNovo uses Meta's models to **see and plan**, and uses RDKit to **apply and verify**. No AI writes a molecule.

## How Meta's models are used

| Model | Job | Built-in check |
|---|---|---|
| **SAM 3.1** | Finds every structure in a figure from a paper | Each crop is shown to the user beside the result |
| **Muse Wonder** | Reads each structure as a SMILES string, twice at different reasoning effort | Two agreeing reads earn a green badge. A single read or a disagreement turns amber. RDKit rejects invalid molecules. The user confirms against an RDKit redraw |
| **Muse Spark 1.3** | Chooses the next edit from an approved menu, using your goals and matched-pair statistics | Cannot write SMILES. Its edit is applied by RDKit and checked by guardrails. If a call fails, a rule-based planner takes over |
| **Muse Image** | Made the hero artwork and the PDF cover | Decoration only. It draws no chemistry |

Everything chemical (properties, edits, validity, drawings, statistics) is computed by RDKit.

## What you can do

1. **Read figures.** Upload a figure with many structures. SAM finds them, Wonder reads them, RDKit checks them, and each result shows a badge as it arrives.
2. **Set the goal.** Choose a profile (oral, brain-penetrant, gut-restricted or custom), lock the groups to protect, and decide how close to stay to your molecule. A live preview shows your molecule and its properties against your limits.
3. **Run a campaign.** Spark proposes an edit, RDKit applies it, and the guardrails accept or reject it. Every rejection is logged with its reason.
4. **See the evidence.** Each step shows matched-pair statistics beside Spark's rationale. The numbers come from code, not from the model.
5. **Save and share.** Download the campaign as a project file, reopen it later with no model calls, or export a PDF report.

## Guardrails (enforced in code)

- Protected groups cannot be removed.
- The ring skeleton must be kept, and at most one ring C-to-N swap is allowed.
- A minimum similarity to the starting molecule.
- No new Lipinski, Veber or structural-alert violations.
- Each edit must move the molecule toward your target profile.
- The campaign stops when the goals are met.

## Results

| Test | Result |
|---|---|
| SAM 3.1 on a 5-structure alkaloid figure | 5 of 5 structures found |
| Muse Wonder on 6 computer-drawn molecules, no names shown | 6 of 6 read correctly (checked by RDKit) |
| Muse Wonder, two reads each, on 5 real alkaloid drawings | 4 agreed on a plausible structure. 1 (strychnine) returned a single read and was flagged for review |
| Matched-pair evidence, 5-fold cross-validation on 245 held-out EGFR pairs | 65% correct on direction of potency change, against 57% for a majority baseline |

The evidence gain is concentrated in one edit: adding a hydroxyl (70% against 30%, n=50). For the other covered edits the evidence matched the baseline, so it shows the chemist what usually happens without adding extra predictive power. We report this so users know where the evidence helps most.

## Scope of this version

MolDeNovo was built in 10 days. This version is designed for:

- **Evidence from EGFR potency.** The matched-pair statistics come from 3,806 EGFR compounds (ChEMBL CHEMBL203) and measure potency. They are most relevant to EGFR-like molecules.
- **Developability and evidence-informed design.** It uses property rules, structural alerts and matched-pair data. It does not model binding.
- **Six evidence-backed edits** from the eight-edit menu. The edits without evidence say so on their card, and edits with fewer than 30 pairs are labelled accordingly.
- **Locked groups.** Only the groups you lock are enforced. Anything Spark says about a group being "essential for activity" is its own reasoning.
- **Human confirmation of figure reads.** Complex structures can be misread, so every figure result is shown beside its source for you to confirm.

## Roadmap

- Docking against a real binding pocket, using the protein structure.
- Trained ADMET models with applicability-domain flags.
- Matched-pair evidence for ring swaps and ester-to-amide, plus support for more targets and properties such as solubility.
- A third tie-break read when Wonder's two reads disagree.
- A scaffold check that knows which ring atoms bind the target.
- Shareable project links, and storing uploaded figures with project files.

## What was built during the hackathon

All code in this repository was written during the hackathon: the chemistry engine, edit library, campaign loop and guardrails, Spark planner, SAM and Wonder pipelines, matched-pair miner and held-out test, project save and open, PDF report, and the website. RDKit, ChEMBL data and the Meta models are third-party. The code was written with AI coding assistance (Claude).

## Data and licences

- Activity data: ChEMBL (CHEMBL203), licensed CC BY-SA 3.0. https://www.ebi.ac.uk/chembl/
- Chemistry: RDKit (BSD).
- Code: MIT.

## Run it yourself (optional)

The hosted version above is the easiest way to try it. To run locally on Windows (PowerShell), you need Python 3.10+, Node 18+ and a Meta Model API key.

```
git clone https://github.com/CharlesDiovu/moldenovo-ai.git
cd moldenovo-ai\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend\.env` with one line (never commit it):

```
MODEL_API_KEY=your_key_here
```

The matched-pair statistics file `backend/data/mmp_stats.csv` is included. To rebuild it from ChEMBL, run `scripts/download_chembl_colab.py` in Google Colab, put the resulting `chembl_series.csv` in `backend\data\`, and run `python mmp.py` (and optionally `python retro_test.py`).

Start the app in two terminals:

```
cd backend ; .\venv\Scripts\Activate.ps1 ; uvicorn main:app --reload
cd frontend ; npm install ; npm run dev
```

Open http://localhost:3000. Set `NEXT_PUBLIC_API_URL` in the frontend to point at a different backend.
