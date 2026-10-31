"use client";

import { useEffect, useRef, useState } from "react";

const API = "http://127.0.0.1:8000";

const GROUP_LABELS: Record<string, string> = {
  carboxylic_acid: "Carboxylic acid",
  ester: "Ester",
  primary_amide: "Primary amide",
};

type Report = {
  smiles: string;
  mw: number;
  logp: number;
  tpsa: number;
  qed: number;
  structural_alerts: string[];
};

type Step = {
  step: number;
  edit_name: string;
  rationale: string;
  planner: string;
  evidence?: {
    summary: string;
    enough: boolean;
    covered: boolean;
    series: string;
  } | null;
  before: Report;
  after: Report;
  qed_change: number;
  similarity_to_start: number;
};

type Rejection = {
  step: number;
  edit_id: string;
  reason: string;
};

type Campaign = {
  start: Report;
  steps: Step[];
  rejections: Rejection[];
  final: Report;
  stop_reason: string;
  goals_met?: boolean;
};

type ReadResult = {
  valid: boolean;
  smiles?: string;
  raw_guess?: string;
  confidence?: string;
  notes?: string;
  model?: string;
  error?: string;
};

type FigureRead = {
  effort: string;
  smiles: string | null;
  confidence: string;
  error: string | null;
};

type FigureCard = {
  index: number;
  crop_png: string;
  status: "agreed" | "single" | "disagree" | "failed";
  valid: boolean;
  smiles: string | null;
  confidence: string;
  notes: string;
  reads: FigureRead[];
};

type FigureItem = {
  id: number;
  name: string;
  previewUrl: string;
  loading: boolean;
  error?: string;
  found?: number;
  capped?: boolean;
  cards?: FigureCard[];
};

const STATUS_STYLE: Record<string, { label: string; cls: string }> = {
  agreed: {
    label: "Two reads agree",
    cls: "bg-emerald-50 text-emerald-800 border-emerald-200",
  },
  single: {
    label: "One read only: check carefully",
    cls: "bg-amber-50 text-amber-800 border-amber-200",
  },
  disagree: {
    label: "Reads disagree: check carefully",
    cls: "bg-amber-50 text-amber-800 border-amber-200",
  },
  failed: {
    label: "Could not read",
    cls: "bg-red-50 text-red-700 border-red-200",
  },
};

/* ---------- shared look ---------- */
const GLASS =
  "rounded-[28px] border border-white/70 bg-white/55 shadow-[0_10px_40px_rgba(14,116,144,0.10)] backdrop-blur-xl";
const PILL =
  "rounded-full bg-[#0f8b8d] px-6 py-3 font-medium text-white shadow-sm transition hover:bg-[#0c7274] disabled:opacity-50";
const PILL_SMALL =
  "rounded-full bg-[#0f8b8d] px-4 py-1.5 text-sm font-medium text-white transition hover:bg-[#0c7274]";
const PILL_OUTLINE =
  "cursor-pointer rounded-full border border-[#0f8b8d] bg-white/50 px-5 py-2 text-sm font-medium text-[#0b6f71] transition hover:bg-white/80";
const NAVY = "text-[#0b1f3a]";

const HOW_IT_WORKS = [
  {
    n: "01",
    model: "SAM 3.1",
    tag: "Meta",
    text: "Finds every structure in a figure from a paper.",
  },
  {
    n: "02",
    model: "Muse Wonder",
    tag: "Meta",
    text: "Reads each structure twice. Two agreeing reads earn a green badge.",
  },
  {
    n: "03",
    model: "Muse Spark",
    tag: "Meta",
    text: "Plans each edit from your goals and real matched-pair data.",
  },
  {
    n: "04",
    model: "RDKit",
    tag: "Open source",
    text: "Applies and checks every molecule. No AI writes chemistry.",
  },
];

function HeroArt() {
  const [ok, setOk] = useState(true);
  if (ok) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src="/hero.png"
        alt=""
        onError={() => setOk(false)}
        className="h-full w-full rounded-[32px] object-cover"
      />
    );
  }
  // Fallback drawn with SVG: soft glass spheres and hexagons.
  return (
    <svg viewBox="0 0 600 460" className="h-full w-full" aria-hidden="true">
      <defs>
        <radialGradient id="sphereA" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#9be8e4" />
          <stop offset="55%" stopColor="#1fa7ad" />
          <stop offset="100%" stopColor="#0b6f85" />
        </radialGradient>
        <radialGradient id="sphereB" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#c9f4f0" />
          <stop offset="60%" stopColor="#58c9c4" />
          <stop offset="100%" stopColor="#17808d" />
        </radialGradient>
        <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#a8dff0" stopOpacity="0.35" />
        </linearGradient>
      </defs>
      <circle cx="390" cy="250" r="165" fill="url(#glass)" stroke="#ffffff" strokeWidth="3" />
      <circle cx="345" cy="285" r="95" fill="url(#sphereA)" />
      <circle cx="430" cy="205" r="70" fill="url(#sphereB)" />
      <circle cx="300" cy="215" r="48" fill="url(#sphereB)" opacity="0.9" />
      <g fill="url(#glass)" stroke="#ffffff" strokeWidth="2">
        <polygon points="520,70 548,86 548,118 520,134 492,118 492,86" />
        <polygon points="470,35 490,46 490,69 470,80 450,69 450,46" />
        <polygon points="545,150 565,161 565,184 545,195 525,184 525,161" />
      </g>
      <circle cx="140" cy="120" r="10" fill="#bdeef0" opacity="0.8" />
      <circle cx="95" cy="330" r="16" fill="#bdeef0" opacity="0.6" />
    </svg>
  );
}

function BackdropHexes() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 -z-10 h-full w-full"
      aria-hidden="true"
    >
      <defs>
        <pattern id="hexpat" width="56" height="97" patternUnits="userSpaceOnUse" patternTransform="scale(1.3)">
          <path
            d="M28 0 L56 16 L56 48 L28 64 L0 48 L0 16 Z M28 64 L28 97 M0 48 L0 81 M56 48 L56 81"
            fill="none"
            stroke="#8fd3dc"
            strokeWidth="1"
            opacity="0.35"
          />
        </pattern>
        <linearGradient id="fadeMask" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="1" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <mask id="fade">
          <rect width="100%" height="100%" fill="url(#fadeMask)" />
        </mask>
      </defs>
      <rect width="100%" height="100%" fill="url(#hexpat)" mask="url(#fade)" />
    </svg>
  );
}

function MolImage({ smiles, label }: { smiles: string; label: string }) {
  return (
    <div className="rounded-2xl bg-white/80 p-3 text-center">
      <div className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`${API}/draw?smiles=${encodeURIComponent(smiles)}`}
        alt={smiles}
        className="mx-auto h-48 w-full object-contain"
      />
    </div>
  );
}

function Delta({ label, a, b }: { label: string; a: number; b: number }) {
  const d = b - a;
  return (
    <div className="rounded-xl bg-white/70 px-3 py-2 text-sm">
      <div className="text-slate-500">{label}</div>
      <div className="font-semibold">
        {a} → {b}{" "}
        <span className="text-[#0b6f71]">
          ({d >= 0 ? "+" : ""}
          {d.toFixed(2)})
        </span>
      </div>
    </div>
  );
}

export default function Home() {
  const [smiles, setSmiles] = useState("CC(C)Cc1ccc(cc1)C(C)C(=O)O");
  const [similarity, setSimilarity] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Campaign | null>(null);

  // Single-structure upload
  const [reading, setReading] = useState(false);
  const [uploadUrl, setUploadUrl] = useState("");
  const [readResult, setReadResult] = useState<ReadResult | null>(null);

  // Multi-figure upload
  const [figures, setFigures] = useState<FigureItem[]>([]);
  const [figureBusy, setFigureBusy] = useState(false);
  const [usedNote, setUsedNote] = useState("");

  // Protected groups, target profile, stop rule
  const [availableGroups, setAvailableGroups] = useState<string[]>([]);
  const [protectedSel, setProtectedSel] = useState<string[]>([]);
  const [logpMax, setLogpMax] = useState(3);
  const [tpsaMax, setTpsaMax] = useState(100);
  const [stopWhenMet, setStopWhenMet] = useState(true);

  // Project file import
  const pendingProtected = useRef<string[] | null>(null);
  const [projectNote, setProjectNote] = useState("");

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API}/groups?smiles=${encodeURIComponent(smiles)}`
        );
        const data = await res.json();
        const found: string[] = data.groups ?? [];
        setAvailableGroups(found);
        if (pendingProtected.current) {
          setProtectedSel(
            pendingProtected.current.filter((g) => found.includes(g))
          );
          pendingProtected.current = null;
        } else {
          setProtectedSel(found);
        }
      } catch {
        setAvailableGroups([]);
        setProtectedSel([]);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [smiles]);

  function patchFigure(id: number, patch: Partial<FigureItem>) {
    setFigures((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  }

  async function handleFigures(files: File[]) {
    setFigureBusy(true);
    const base = Date.now();
    const items: FigureItem[] = files.map((f, i) => ({
      id: base + i,
      name: f.name,
      previewUrl: URL.createObjectURL(f),
      loading: true,
    }));
    setFigures((prev) => [...items, ...prev]);

    for (let i = 0; i < files.length; i++) {
      const id = items[i].id;
      try {
        const form = new FormData();
        form.append("file", files[i]);
        const res = await fetch(`${API}/read-figure`, {
          method: "POST",
          body: form,
        });
        const data = await res.json();
        if (data.error) {
          patchFigure(id, { loading: false, error: data.error });
        } else {
          patchFigure(id, {
            loading: false,
            found: data.found,
            capped: data.capped,
            cards: data.cards,
          });
        }
      } catch {
        patchFigure(id, {
          loading: false,
          error: "Could not reach the backend. Is uvicorn running?",
        });
      }
    }
    setFigureBusy(false);
  }

  function useMolecule(s: string) {
    setSmiles(s);
    setResult(null);
    setProjectNote("");
    setUsedNote(`Loaded into the starting molecule box: ${s}`);
    document
      .getElementById("workbench")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function handleUpload(file: File) {
    setReading(true);
    setReadResult(null);
    setUploadUrl(URL.createObjectURL(file));
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/read-structure`, {
        method: "POST",
        body: form,
      });
      setReadResult(await res.json());
    } catch {
      setReadResult({
        valid: false,
        error: "Could not reach the backend. Is uvicorn running?",
      });
    }
    setReading(false);
  }

  function acceptRead() {
    if (readResult?.smiles) useMolecule(readResult.smiles);
    setReadResult(null);
    setUploadUrl("");
  }

  function discardRead() {
    setReadResult(null);
    setUploadUrl("");
  }

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    setProjectNote("");
    try {
      const res = await fetch(`${API}/campaign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smiles,
          max_steps: 3,
          use_spark: true,
          protected: protectedSel,
          logp_max: logpMax,
          tpsa_max: tpsaMax,
          stop_when_met: stopWhenMet,
          min_similarity: similarity,
        }),
      });
      const data = await res.json();
      if (data.error) setError(data.error);
      else setResult(data);
    } catch {
      setError("Could not reach the backend. Is uvicorn running?");
    }
    setLoading(false);
  }

  function exportProject() {
    if (!result) return;
    const project = {
      format: "moldenovo-project",
      version: 1,
      saved_at: new Date().toISOString(),
      settings: {
        smiles,
        min_similarity: similarity,
        logp_max: logpMax,
        tpsa_max: tpsaMax,
        protected: protectedSel,
        stop_when_met: stopWhenMet,
      },
      models: {
        planner: "muse-spark-1.3",
        figure_reading: "muse-wonder-1.0",
        segmentation: "sam-3.1",
        chemistry: "RDKit",
      },
      result,
    };
    const blob = new Blob([JSON.stringify(project, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moldenovo-project-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setProjectNote("Project file downloaded.");
  }

  async function importProject(file: File) {
    try {
      const data = JSON.parse(await file.text());
      if (data.format !== "moldenovo-project" || !data.result || !data.settings) {
        setProjectNote("That file is not a MolDeNovo project.");
        return;
      }
      const s = data.settings;
      pendingProtected.current = Array.isArray(s.protected) ? s.protected : [];
      setSmiles(s.smiles ?? smiles);
      setSimilarity(s.min_similarity ?? 0.4);
      setLogpMax(s.logp_max ?? 3);
      setTpsaMax(s.tpsa_max ?? 100);
      setStopWhenMet(s.stop_when_met ?? true);
      setResult(data.result as Campaign);
      setError("");
      setUsedNote("");
      setProjectNote(
        `Loaded project saved ${data.saved_at ?? "earlier"}. No models were called.`
      );
      document
        .getElementById("workbench")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {
      setProjectNote("Could not read that file.");
    }
  }

  return (
    <main
      className="relative min-h-screen overflow-hidden text-slate-900"
      style={{
        fontFamily:
          "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        background:
          "radial-gradient(900px 500px at 85% -5%, #c6f0f1 0%, rgba(198,240,241,0) 60%), radial-gradient(700px 500px at 0% 40%, #dff5f3 0%, rgba(223,245,243,0) 60%), linear-gradient(180deg, #e9fafb 0%, #ffffff 55%, #e4f6f5 100%)",
      }}
    >
      <BackdropHexes />

      {/* NAV */}
      <header className="mx-auto flex max-w-6xl items-center px-6 pt-8">
        <div className={`text-lg font-semibold tracking-[0.35em] ${NAVY}`}>
          MOLDENOVO
        </div>
        <nav className="ml-auto hidden items-center gap-8 text-sm text-slate-700 sm:flex">
          <a href="#how" className="hover:text-[#0b6f71]">How it works</a>
          <a href="#workbench" className="hover:text-[#0b6f71]">Workbench</a>
          <a
            href="#workbench"
            className="rounded-full bg-[#0b2a4a] px-5 py-2 text-white transition hover:bg-[#0b1f3a]"
          >
            Start a campaign
          </a>
        </nav>
      </header>

      {/* HERO */}
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-16 pt-14 md:grid-cols-2">
        <div>
          <h1
            className={`text-5xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl ${NAVY}`}
          >
            Medicinal chemistry,
            <br />
            checked at every step.
          </h1>
          <p className="mt-6 max-w-md text-lg text-slate-700">
            An evidence-grounded copilot for lead optimisation. Meta’s Muse
            models plan the edits. RDKit applies and verifies every one.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a href="#workbench" className={`${PILL} inline-block`}>
              Open the workbench →
            </a>
            <a
              href="#how"
              className="text-sm font-medium text-[#0b2a4a] underline underline-offset-4"
            >
              See how it works
            </a>
          </div>
          <div className="mt-10 flex flex-wrap gap-6 text-sm text-slate-700">
            <span>✓ Evidence-led</span>
            <span>✓ Guardrails you control</span>
            <span>✓ Every claim traceable</span>
          </div>
        </div>
        <div className="relative h-[340px] sm:h-[420px]">
          <div className={`${GLASS} absolute inset-0 overflow-hidden p-2`}>
            <HeroArt />
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="mx-auto max-w-6xl px-6 pb-16">
        <p className="text-xs font-medium uppercase tracking-[0.3em] text-slate-500">
          How it works
        </p>
        <h2 className={`mt-3 text-4xl font-extrabold tracking-tight ${NAVY}`}>
          Four tools, one checked pipeline.
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS.map((h) => (
            <div key={h.n} className={`${GLASS} p-5`}>
              <div className="flex items-center text-xs text-slate-500">
                <span>{h.n}</span>
                <span className="ml-auto rounded-full bg-[#e3f6f6] px-2.5 py-0.5 text-[11px] font-medium text-[#0b6f71]">
                  {h.tag}
                </span>
              </div>
              <h3 className={`mt-4 text-lg font-bold ${NAVY}`}>{h.model}</h3>
              <p className="mt-1 text-sm text-slate-600">{h.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* WORKBENCH */}
      <section id="workbench" className="mx-auto max-w-4xl scroll-mt-8 px-6 pb-20">
        <p className="text-xs font-medium uppercase tracking-[0.3em] text-slate-500">
          Workbench
        </p>
        <h2 className={`mt-3 text-4xl font-extrabold tracking-tight ${NAVY}`}>
          Start with a clearer picture.
        </h2>

        {/* INPUT CARD */}
        <div className={`${GLASS} mt-8 p-6`}>
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">
              Starting molecule (SMILES)
            </label>
            <label className="ml-auto cursor-pointer rounded-full border border-slate-300 bg-white/50 px-4 py-1 text-xs font-medium text-slate-700 hover:bg-white/80">
              Open a project file
              <input
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importProject(f);
                  e.target.value = "";
                }}
              />
            </label>
          </div>
          <input
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white/90 px-4 py-3 font-mono text-sm outline-none focus:border-[#0f8b8d]"
          />
          {usedNote && <p className="mt-2 text-xs text-[#0b6f71]">{usedNote}</p>}
          {projectNote && (
            <p className="mt-2 text-xs text-[#0b6f71]">{projectNote}</p>
          )}

          {/* UPLOAD BUTTONS */}
          <div className="mt-4 flex flex-wrap gap-3">
            <label className={PILL_OUTLINE}>
              {reading
                ? "Muse Wonder is reading..."
                : "Upload one molecule drawing"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                disabled={reading}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleUpload(f);
                  e.target.value = "";
                }}
              />
            </label>

            <label className="inline-block cursor-pointer rounded-full bg-[#0f8b8d] px-5 py-2 text-sm font-medium text-white transition hover:bg-[#0c7274]">
              {figureBusy
                ? "SAM + Wonder are working..."
                : "Upload figures with many molecules"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                multiple
                className="hidden"
                disabled={figureBusy}
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []);
                  if (files.length) handleFigures(files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>

          {/* CONFIRM WHAT WE READ (single drawing) */}
          {readResult && (
            <div className="mt-5 rounded-2xl border border-white/80 bg-white/70 p-4">
              {readResult.valid && readResult.smiles ? (
                <>
                  <div className="flex items-center gap-2">
                    <h3 className={`font-semibold ${NAVY}`}>
                      Is this your molecule?
                    </h3>
                    <span className="ml-auto rounded-full bg-[#e3f6f6] px-3 py-1 text-xs font-medium text-[#0b6f71]">
                      Read by {readResult.model} · confidence{" "}
                      {readResult.confidence}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-white p-3 text-center">
                      <div className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                        Your upload
                      </div>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={uploadUrl}
                        alt="Your upload"
                        className="mx-auto h-48 w-full object-contain"
                      />
                    </div>
                    <MolImage
                      smiles={readResult.smiles}
                      label="What we understood (redrawn by RDKit)"
                    />
                  </div>
                  <p className="mt-3 font-mono text-xs text-slate-500">
                    {readResult.smiles}
                  </p>
                  {readResult.notes && (
                    <p className="mt-2 text-xs text-slate-600">
                      Model notes: {readResult.notes}
                    </p>
                  )}
                  <p className="mt-2 text-xs text-slate-500">
                    Compare the two drawings carefully. Vision models can
                    misread structures, and a valid molecule is not always the
                    right one.
                  </p>
                  <div className="mt-4 flex gap-3">
                    <button onClick={acceptRead} className={PILL_SMALL}>
                      Yes, use this molecule
                    </button>
                    <button
                      onClick={discardRead}
                      className="rounded-full border border-slate-300 bg-white/60 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-white"
                    >
                      No, discard
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-sm text-red-600">{readResult.error}</p>
                  {readResult.raw_guess && (
                    <p className="mt-1 font-mono text-xs text-slate-500">
                      Model said: {readResult.raw_guess}
                    </p>
                  )}
                  <button
                    onClick={discardRead}
                    className="mt-3 rounded-full border border-slate-300 bg-white/60 px-4 py-1.5 text-sm text-slate-700 hover:bg-white"
                  >
                    Dismiss
                  </button>
                </>
              )}
            </div>
          )}

          {/* TARGET PROFILE */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-slate-600">
              Target profile: maximum LogP{" "}
              <span className="font-semibold text-[#0b6f71]">
                {logpMax.toFixed(1)}
              </span>
              <input
                type="range"
                min={1}
                max={5}
                step={0.5}
                value={logpMax}
                onChange={(e) => setLogpMax(parseFloat(e.target.value))}
                className="mt-2 w-full accent-[#0f8b8d]"
              />
            </label>
            <label className="text-sm font-medium text-slate-600">
              Maximum TPSA{" "}
              <span className="font-semibold text-[#0b6f71]">{tpsaMax}</span>
              <input
                type="range"
                min={40}
                max={140}
                step={10}
                value={tpsaMax}
                onChange={(e) => setTpsaMax(parseFloat(e.target.value))}
                className="mt-2 w-full accent-[#0f8b8d]"
              />
            </label>
          </div>

          <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="accent-[#0f8b8d]"
              checked={stopWhenMet}
              onChange={(e) => setStopWhenMet(e.target.checked)}
            />
            Stop when goals are met (recommended)
          </label>

          {/* PROTECTED GROUPS */}
          <div className="mt-6">
            <div className="text-sm font-medium text-slate-600">
              Protect these groups (the AI may not remove them)
            </div>
            {availableGroups.length === 0 ? (
              <p className="mt-1 text-xs text-slate-500">
                None of the protectable groups were found in this molecule.
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-4">
                {availableGroups.map((g) => (
                  <label key={g} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="accent-[#0f8b8d]"
                      checked={protectedSel.includes(g)}
                      onChange={(e) =>
                        setProtectedSel((prev) =>
                          e.target.checked
                            ? [...prev, g]
                            : prev.filter((x) => x !== g)
                        )
                      }
                    />
                    {GROUP_LABELS[g] ?? g}
                  </label>
                ))}
              </div>
            )}
          </div>

          <label className="mt-6 block text-sm font-medium text-slate-600">
            How far may the AI wander from your molecule? Minimum similarity:{" "}
            <span className="font-semibold text-[#0b6f71]">
              {similarity.toFixed(2)}
            </span>
          </label>
          <input
            type="range"
            min={0.2}
            max={0.9}
            step={0.05}
            value={similarity}
            onChange={(e) => setSimilarity(parseFloat(e.target.value))}
            className="mt-2 w-full accent-[#0f8b8d]"
          />
          <div className="flex justify-between text-xs text-slate-500">
            <span>Explore freely</span>
            <span>Stay very close</span>
          </div>

          <button onClick={run} disabled={loading} className={`${PILL} mt-6`}>
            {loading
              ? "Muse Spark is planning (about a minute)..."
              : "Run optimization campaign →"}
          </button>
          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        </div>

        {/* FIGURE RESULTS */}
        {figures.length > 0 && (
          <div className="mt-12">
            <h2 className={`text-2xl font-extrabold tracking-tight ${NAVY}`}>
              Structures found in your figures
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              SAM 3.1 finds each structure, Muse Wonder reads it twice, and
              RDKit checks every answer. Always compare the crop with the
              redraw before using a molecule.
            </p>

            {figures.map((fig) => (
              <div key={fig.id} className="mt-6">
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={fig.previewUrl}
                    alt={fig.name}
                    className="h-14 w-14 rounded-lg border border-white object-cover"
                  />
                  <div>
                    <div className="text-sm font-semibold">{fig.name}</div>
                    <div className="text-xs text-slate-500">
                      {fig.loading
                        ? "Working. A figure can take a few minutes."
                        : fig.error
                        ? "Failed"
                        : `${fig.found} structure(s) found${
                            fig.capped ? " (showing the first 12)" : ""
                          }`}
                    </div>
                  </div>
                </div>

                {fig.error && (
                  <p className="mt-2 text-sm text-red-600">{fig.error}</p>
                )}

                {fig.cards && (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    {fig.cards.map((c) => {
                      const st = STATUS_STYLE[c.status] ?? STATUS_STYLE.failed;
                      return (
                        <div key={c.index} className={`${GLASS} p-4`}>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold">
                              Structure {c.index + 1}
                            </span>
                            <span
                              className={`ml-auto rounded-full border px-3 py-1 text-xs font-medium ${st.cls}`}
                            >
                              {st.label}
                            </span>
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-2">
                            <div className="rounded-2xl bg-white p-2 text-center">
                              <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-slate-500">
                                Crop from figure
                              </div>
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img
                                src={`data:image/png;base64,${c.crop_png}`}
                                alt="crop"
                                className="mx-auto h-32 w-full object-contain"
                              />
                            </div>
                            {c.smiles ? (
                              <div className="rounded-2xl bg-white p-2 text-center">
                                <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-slate-500">
                                  Redrawn by RDKit
                                </div>
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={`${API}/draw?smiles=${encodeURIComponent(
                                    c.smiles
                                  )}&width=260&height=200`}
                                  alt={c.smiles}
                                  className="mx-auto h-32 w-full object-contain"
                                />
                              </div>
                            ) : (
                              <div className="flex items-center justify-center rounded-2xl bg-white p-2 text-center text-xs text-slate-500">
                                No valid molecule was read
                              </div>
                            )}
                          </div>

                          {c.smiles && (
                            <p className="mt-2 break-all font-mono text-[11px] text-slate-500">
                              {c.smiles}
                            </p>
                          )}
                          <p className="mt-1 text-xs text-slate-500">
                            Model confidence: {c.confidence}
                          </p>

                          {c.status === "disagree" && (
                            <div className="mt-2 rounded-xl bg-amber-50 p-2 text-[11px] text-amber-900">
                              The two reads gave different molecules:
                              {c.reads.map((r, i) => (
                                <div key={i} className="break-all font-mono">
                                  {r.effort}: {r.smiles ?? r.error}
                                </div>
                              ))}
                            </div>
                          )}

                          {c.status === "failed" && (
                            <p className="mt-2 text-xs text-red-600">
                              {c.reads
                                .map((r) => r.error)
                                .filter(Boolean)[0] ?? "Both reads failed."}{" "}
                              Type the SMILES yourself if you know it.
                            </p>
                          )}

                          {c.smiles && (
                            <button
                              onClick={() => useMolecule(c.smiles as string)}
                              className={`${PILL_SMALL} mt-3`}
                            >
                              Use this molecule
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* CAMPAIGN RESULTS */}
        {result && (
          <div className="mt-12">
            <div className="flex items-center gap-3">
              <h2 className={`text-3xl font-extrabold tracking-tight ${NAVY}`}>
                Campaign timeline
              </h2>
              <button
                onClick={exportProject}
                className="ml-auto rounded-full border border-[#0f8b8d] bg-white/50 px-4 py-1.5 text-sm font-medium text-[#0b6f71] hover:bg-white/80"
              >
                Save project file
              </button>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Start: <span className="font-mono">{result.start.smiles}</span> ·
              QED {result.start.qed} · LogP {result.start.logp}
            </p>

            <div className="mt-4 max-w-xs">
              <MolImage smiles={result.start.smiles} label="Starting molecule" />
            </div>

            {result.steps.length === 0 && (
              <p className={`${GLASS} mt-6 p-4 text-sm`}>
                {result.stop_reason.startsWith("The starting molecule")
                  ? result.stop_reason
                  : "No edit passed the guardrails. Try lowering the similarity slider."}
              </p>
            )}

            <ol className="mt-6 space-y-5">
              {result.steps.map((s) => (
                <li key={s.step} className={`${GLASS} p-5`}>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0f8b8d] text-sm font-semibold text-white">
                      {s.step}
                    </span>
                    <h3 className={`text-lg font-bold ${NAVY}`}>{s.edit_name}</h3>
                    <span className="ml-auto rounded-full bg-[#e3f6f6] px-3 py-1 text-xs font-medium text-[#0b6f71]">
                      Planner: {s.planner}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-700">{s.rationale}</p>
                  {s.evidence && (
                    <div
                      className={`mt-3 rounded-xl border p-3 text-xs ${
                        s.evidence.enough
                          ? "border-teal-100 bg-teal-50/60 text-teal-900"
                          : "border-slate-200 bg-slate-50 text-slate-600"
                      }`}
                    >
                      <div className="font-semibold">
                        Evidence from real data (computed by RDKit, not by the AI)
                      </div>
                      <div className="mt-1">{s.evidence.summary}</div>
                      <div className="mt-1 text-[11px] opacity-70">
                        Series: {s.evidence.series}. This measures EGFR potency,
                        not solubility or metabolism.
                      </div>
                    </div>
                  )}
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <MolImage smiles={s.before.smiles} label="Before" />
                    <MolImage smiles={s.after.smiles} label="After" />
                  </div>
                  <p className="mt-3 font-mono text-xs text-slate-500">
                    {s.after.smiles}
                  </p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Delta label="QED" a={s.before.qed} b={s.after.qed} />
                    <Delta label="LogP" a={s.before.logp} b={s.after.logp} />
                    <Delta label="TPSA" a={s.before.tpsa} b={s.after.tpsa} />
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    Similarity to start: {s.similarity_to_start}
                  </p>
                </li>
              ))}
            </ol>

            <p className="mt-6 text-sm text-slate-600">
              Stopped because: {result.stop_reason}
            </p>

            <details className={`${GLASS} mt-6 p-4`}>
              <summary className="cursor-pointer text-sm font-semibold text-slate-700">
                Rejected ideas ({result.rejections.length})
              </summary>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                {result.rejections.map((r, i) => (
                  <li key={i}>
                    Step {r.step} · <b>{r.edit_id}</b> — {r.reason}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}
      </section>

      {/* FOOTER */}
      <footer className="mx-auto max-w-6xl border-t border-white/70 px-6 pb-10 pt-6">
        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
          <span className={`font-semibold tracking-[0.3em] ${NAVY}`}>MOLDENOVO</span>
          <span>
            Muse Image made the hero artwork only. All chemistry comes from RDKit.
          </span>
          <span className="ml-auto">
            Optimises developability and evidence-informed design, not binding.
          </span>
        </div>
      </footer>
    </main>
  );
}