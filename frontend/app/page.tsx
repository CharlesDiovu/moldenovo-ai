"use client";

import { useState } from "react";

const API = "http://127.0.0.1:8000";

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
        <span className="text-teal-700">
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

  // Upload / vision state
  const [reading, setReading] = useState(false);
  const [uploadUrl, setUploadUrl] = useState("");
  const [readResult, setReadResult] = useState<ReadResult | null>(null);

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
    if (readResult?.smiles) setSmiles(readResult.smiles);
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
    try {
      const res = await fetch(`${API}/campaign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smiles,
          max_steps: 3,
          use_spark: true,
          protected: ["carboxylic_acid"],
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

  return (
    <main
      className="min-h-screen px-6 py-12 text-slate-900"
      style={{
        background:
          "linear-gradient(160deg, #e6f9fb 0%, #ffffff 45%, #dff5f3 100%)",
      }}
    >
      <div className="mx-auto max-w-4xl">
        <p className="tracking-[0.3em] text-sm text-slate-600">MOLDENOVO AI</p>
        <h1 className="mt-4 text-5xl font-bold leading-tight text-[#0b1f3a]">
          Design better molecules,
          <br />
          one checked step at a time.
        </h1>

        {/* INPUT CARD */}
        <section className="mt-10 rounded-3xl border border-white bg-white/60 p-6 shadow-sm backdrop-blur">
          <label className="text-sm font-medium text-slate-600">
            Starting molecule (SMILES)
          </label>
          <input
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 font-mono text-sm outline-none focus:border-teal-500"
          />

          {/* UPLOAD */}
          <div className="mt-4">
            <label className="inline-block cursor-pointer rounded-full border border-teal-700 px-5 py-2 text-sm font-medium text-teal-800 transition hover:bg-teal-50">
              {reading ? "Muse Wonder is reading..." : "Or upload a drawing of the molecule"}
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
          </div>

          {/* CONFIRM WHAT WE READ */}
          {readResult && (
            <div className="mt-5 rounded-2xl border border-teal-100 bg-white/80 p-4">
              {readResult.valid && readResult.smiles ? (
                <>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">Is this your molecule?</h3>
                    <span className="ml-auto rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800">
                      Read by {readResult.model} · confidence {readResult.confidence}
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
                    <MolImage smiles={readResult.smiles} label="What we understood (redrawn by RDKit)" />
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
                    <button
                      onClick={acceptRead}
                      className="rounded-full bg-teal-700 px-5 py-2 text-sm font-medium text-white hover:bg-teal-800"
                    >
                      Yes, use this molecule
                    </button>
                    <button
                      onClick={discardRead}
                      className="rounded-full border border-slate-300 px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
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
                    className="mt-3 rounded-full border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Dismiss
                  </button>
                </>
              )}
            </div>
          )}

          <label className="mt-6 block text-sm font-medium text-slate-600">
            How far may the AI wander from your molecule? Minimum similarity:{" "}
            <span className="font-semibold text-teal-700">
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
            className="mt-2 w-full accent-teal-600"
          />
          <div className="flex justify-between text-xs text-slate-500">
            <span>Explore freely</span>
            <span>Stay very close</span>
          </div>

          <button
            onClick={run}
            disabled={loading}
            className="mt-6 rounded-full bg-teal-700 px-6 py-3 font-medium text-white transition hover:bg-teal-800 disabled:opacity-50"
          >
            {loading
              ? "Muse Spark is planning (about a minute)..."
              : "Run optimization campaign →"}
          </button>
          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        </section>

        {/* RESULTS */}
        {result && (
          <section className="mt-10">
            <h2 className="text-2xl font-bold text-[#0b1f3a]">
              Campaign timeline
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Start: <span className="font-mono">{result.start.smiles}</span> ·
              QED {result.start.qed} · LogP {result.start.logp}
            </p>

            <div className="mt-4 max-w-xs">
              <MolImage smiles={result.start.smiles} label="Starting molecule" />
            </div>

            {result.steps.length === 0 && (
              <p className="mt-6 rounded-2xl bg-white/70 p-4 text-sm">
                No edit passed the guardrails. Try lowering the similarity
                slider.
              </p>
            )}

            <ol className="mt-6 space-y-5">
              {result.steps.map((s) => (
                <li
                  key={s.step}
                  className="rounded-3xl border border-white bg-white/60 p-5 shadow-sm backdrop-blur"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-sm font-semibold text-white">
                      {s.step}
                    </span>
                    <h3 className="text-lg font-semibold">{s.edit_name}</h3>
                    <span className="ml-auto rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800">
                      Planner: {s.planner}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-700">{s.rationale}</p>
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

            <details className="mt-6 rounded-2xl bg-white/60 p-4">
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
          </section>
        )}
      </div>
    </main>
  );
}