"use client";

/** Module I — Comparables boursiers : bêtas (régression, désendetté) + multiples.
 *
 * Le job tourne côté backend (progression par société) ; l'exclusion d'un comparable
 * recalcule les stats via /api/comparables/stats sans aucun re-téléchargement.
 */

import { useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  type CompanyRecord,
  type ComparablesJob,
  downloadExcel,
  pollJob,
  type StatsMap,
} from "@/lib/api";
import { fmtBeta, fmtMillions, fmtMult, fmtPct, ND } from "@/lib/format";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  Field,
  JobProgress,
  PageTitle,
  Select,
  TextArea,
  TextInput,
} from "@/components/ui";

type Mode = "tickers" | "noms";

const COLUMNS: {
  key: keyof CompanyRecord;
  label: string;
  fmt: (v: never) => string;
  align?: "left";
}[] = [
  { key: "name", label: "Société", fmt: (v: string | null) => v ?? ND, align: "left" },
  { key: "market_cap", label: "Capi (M)", fmt: fmtMillions },
  { key: "net_debt", label: "Dette nette (M)", fmt: fmtMillions },
  { key: "enterprise_value", label: "VE (M)", fmt: fmtMillions },
  { key: "beta_source", label: "β publié", fmt: fmtBeta },
  { key: "beta_regression", label: "β régr.", fmt: fmtBeta },
  { key: "r2", label: "R²", fmt: fmtBeta },
  { key: "n_obs", label: "N pts", fmt: (v: number | null) => (v == null ? ND : String(v)) },
  { key: "gearing", label: "Gearing", fmt: (v: number | null) => fmtPct(v) },
  { key: "beta_unlevered", label: "β désend.", fmt: fmtBeta },
  { key: "ev_sales", label: "VE/CA", fmt: fmtMult },
  { key: "ev_ebitda", label: "VE/EBITDA", fmt: fmtMult },
  { key: "ev_ebit", label: "VE/EBIT", fmt: fmtMult },
  { key: "pe_trailing", label: "PER", fmt: fmtMult },
  { key: "pb", label: "P/B", fmt: fmtMult },
];

const STAT_ROWS: { key: keyof StatsMap[string]; label: string }[] = [
  { key: "median", label: "Médiane" },
  { key: "mean", label: "Moyenne" },
  { key: "min", label: "Minimum" },
  { key: "max", label: "Maximum" },
];

export default function ComparablesPage() {
  const [mode, setMode] = useState<Mode>("tickers");
  const [input, setInput] = useState("WMS\nGF.SW\nAALB.AS\nGEN.L\nWIE.VI\nMWA");
  const [taxRate, setTaxRate] = useState("25");
  const [period, setPeriod] = useState("5y");
  const [frequency, setFrequency] = useState("1mo");

  const [job, setJob] = useState<ComparablesJob | null>(null);
  const [phase, setPhase] = useState<"idle" | "resolving" | "running">("idle");
  const [error, setError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<string[]>([]);

  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [stats, setStats] = useState<StatsMap | null>(null);
  const [statsN, setStatsN] = useState(0);
  const [saveLabel, setSaveLabel] = useState("");
  const [savedId, setSavedId] = useState<number | null>(null);
  const [busyExport, setBusyExport] = useState(false);
  const statsTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const records = useMemo(() => job?.records ?? [], [job]);
  const selection = useMemo(
    () => records.filter((r) => !excluded.has(r.ticker)),
    [records, excluded],
  );

  // Stats recalculées (débouncées) à chaque changement de sélection — zéro réseau Yahoo.
  useEffect(() => {
    if (job?.status !== "done") return;
    if (statsTimer.current) clearTimeout(statsTimer.current);
    statsTimer.current = setTimeout(() => {
      api
        .statsFor(selection)
        .then((res) => {
          setStats(res.stats);
          setStatsN(res.n);
        })
        .catch(() => undefined);
    }, 250);
    return () => {
      if (statsTimer.current) clearTimeout(statsTimer.current);
    };
  }, [selection, job?.status]);

  async function launch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSavedId(null);
    setResolved([]);
    setExcluded(new Set());
    setStats(null);
    setJob(null);

    let tickers = input.split("\n").map((l) => l.trim()).filter(Boolean);
    if (tickers.length === 0) {
      setError("Saisir au moins une ligne.");
      return;
    }

    try {
      if (mode === "noms") {
        setPhase("resolving");
        const res = await api.resolveNames(tickers);
        const found = res.results.filter((r) => r.match);
        const missing = res.results.filter((r) => !r.match).map((r) => r.query);
        if (missing.length > 0) {
          setError(`Sans correspondance Yahoo : ${missing.join(", ")}`);
        }
        setResolved(found.map((r) => `${r.query} → ${r.match!.symbol} (${r.match!.name})`));
        tickers = found.map((r) => r.match!.symbol);
        if (tickers.length === 0) {
          setPhase("idle");
          return;
        }
      }

      setPhase("running");
      const created = await api.createComparablesJob({
        tickers,
        tax_rate: Number(taxRate) / 100,
        period,
        frequency,
      });
      setJob(created);
      const finished = await pollJob(() => api.comparablesJob(created.id), setJob);
      if (finished.status === "error") setError(finished.error ?? "Échec du calcul.");
    } catch {
      setError("Échec du lancement — le backend est-il démarré ?");
    } finally {
      setPhase("idle");
    }
  }

  function toggle(ticker: string) {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(ticker)) next.delete(ticker);
      else next.add(ticker);
      return next;
    });
  }

  async function exportSelection() {
    setBusyExport(true);
    try {
      await downloadExcel(selection);
    } catch {
      setError("Export impossible.");
    } finally {
      setBusyExport(false);
    }
  }

  async function saveRun() {
    try {
      const res = await api.saveRun(selection, saveLabel || undefined, job?.params);
      setSavedId(res.id);
    } catch {
      setError("Sauvegarde impossible.");
    }
  }

  const done = job?.status === "done";

  return (
    <div>
      <PageTitle
        kicker="Module I"
        title="Comparables boursiers"
        lede="Bêta de régression (R², nombre de points), bêta désendetté (Hamada) et multiples de
        valorisation d'un échantillon de sociétés cotées. Source : Yahoo Finance — multiples non
        retraités, à utiliser avec le jugement d'un analyste."
      />

      {/* ——— Formulaire ——— */}
      <Card className="p-6">
        <form onSubmit={launch} className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_220px]">
          <div className="space-y-4">
            <div className="flex gap-0 border-b border-hairline">
              {(["tickers", "noms"] as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`label-caps cursor-pointer px-4 py-2 transition-colors ${
                    mode === m
                      ? "border-b-2 border-brass text-ink"
                      : "text-ink-mut hover:text-ink"
                  }`}
                >
                  {m === "tickers" ? "Tickers Yahoo" : "Noms de sociétés"}
                </button>
              ))}
            </div>
            <Field
              label={mode === "tickers" ? "Tickers (un par ligne)" : "Noms (un par ligne)"}
              hint={
                mode === "tickers"
                  ? "Suffixes : .PA Paris, .AS Amsterdam, .L Londres, .SW Suisse, .VI Vienne, .DE Francfort, .MI Milan — sans suffixe : USA."
                  : "Chaque nom est résolu vers son ticker Yahoo (place principale privilégiée)."
              }
            >
              <TextArea value={input} onChange={(e) => setInput(e.target.value)} rows={6} />
            </Field>
          </div>

          <div className="space-y-4">
            <Field label="Taux d'IS (%)">
              <TextInput
                value={taxRate}
                onChange={(e) => setTaxRate(e.target.value)}
                inputMode="decimal"
              />
            </Field>
            <Field label="Période du bêta">
              <Select value={period} onChange={(e) => setPeriod(e.target.value)}>
                <option value="2y">2 ans</option>
                <option value="3y">3 ans</option>
                <option value="5y">5 ans</option>
                <option value="10y">10 ans</option>
              </Select>
            </Field>
            <Field label="Fréquence">
              <Select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
                <option value="1mo">Mensuelle</option>
                <option value="1wk">Hebdomadaire</option>
              </Select>
            </Field>
            <Button type="submit" busy={phase !== "idle"}>
              {phase === "resolving" ? "Résolution…" : "Lancer le calcul"}
            </Button>
          </div>
        </form>

        {resolved.length > 0 && (
          <div className="mt-4 border-t border-hairline pt-3">
            {resolved.map((line) => (
              <p key={line} className="tabular text-xs text-ink-mut">
                {line}
              </p>
            ))}
          </div>
        )}
      </Card>

      <div className="mt-6 space-y-6">
        <ErrorNote message={error} />

        {job && job.status !== "done" && job.status !== "error" && (
          <Card className="p-6">
            <JobProgress
              progress={job.progress}
              total={job.total}
              label="Sociétés traitées"
            />
          </Card>
        )}

        {/* ——— Résultats ——— */}
        {done && records.length > 0 && (
          <>
            <Card className="rise-in overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-ink bg-paper-deep text-left">
                    <th className="px-3 py-2.5 label-caps text-ink-mut">Retenu</th>
                    <th className="px-3 py-2.5 label-caps text-ink-mut">Ticker</th>
                    {COLUMNS.map((c) => (
                      <th
                        key={c.key}
                        className={`px-3 py-2.5 label-caps whitespace-nowrap text-ink-mut ${
                          c.align === "left" ? "text-left" : "text-right"
                        }`}
                      >
                        {c.label}
                      </th>
                    ))}
                    <th className="px-3 py-2.5 label-caps text-ink-mut">Couv.</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => {
                    const off = excluded.has(r.ticker);
                    const cov = job.coverage?.[r.ticker] ?? "ok";
                    return (
                      <tr
                        key={r.ticker}
                        className={`border-b border-hairline transition-opacity hover:bg-paper-deep/50 ${
                          off ? "opacity-35" : ""
                        }`}
                      >
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={!off}
                            onChange={() => toggle(r.ticker)}
                            className="size-4 cursor-pointer accent-[var(--color-brass)]"
                          />
                        </td>
                        <td className="tabular px-3 py-2 font-medium">{r.ticker}</td>
                        {COLUMNS.map((c) => (
                          <td
                            key={c.key}
                            className={`px-3 py-2 whitespace-nowrap ${
                              c.align === "left" ? "" : "tabular text-right"
                            } ${off ? "line-through" : ""}`}
                          >
                            {c.fmt(r[c.key] as never)}
                          </td>
                        ))}
                        <td className="px-3 py-2">
                          <Badge tone={cov === "ok" ? "ok" : cov === "partielle" ? "warn" : "alert"}>
                            {cov}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                {/* Stats sur la sélection */}
                {stats && (
                  <tfoot>
                    {STAT_ROWS.map((row, i) => (
                      <tr
                        key={row.key}
                        className={`bg-paper-deep/70 ${i === 0 ? "border-t-2 border-ink" : ""}`}
                      >
                        <td colSpan={3} className="label-caps px-3 py-2 text-ink-mut">
                          {row.label}
                          {i === 0 && (
                            <span className="tabular ml-2 normal-case tracking-normal">
                              ({statsN} retenues)
                            </span>
                          )}
                        </td>
                        {COLUMNS.slice(1).map((c) => {
                          const s = stats[c.key as string];
                          const v = s ? s[row.key] : null;
                          let text = ND;
                          if (v != null) {
                            if (["market_cap", "net_debt", "enterprise_value"].includes(c.key)) {
                              text = fmtMillions(v);
                            } else if (c.key === "gearing") text = fmtPct(v);
                            else if (["ev_sales", "ev_ebitda", "ev_ebit", "pe_trailing", "pb"].includes(c.key)) {
                              text = fmtMult(v);
                            } else text = fmtBeta(v);
                          }
                          return (
                            <td key={c.key} className="tabular px-3 py-2 text-right font-medium">
                              {text}
                            </td>
                          );
                        })}
                        <td />
                      </tr>
                    ))}
                  </tfoot>
                )}
              </table>
            </Card>

            {/* ——— Actions ——— */}
            <Card className="rise-in flex flex-wrap items-end gap-4 p-5">
              <Button onClick={exportSelection} busy={busyExport}>
                Exporter la sélection (.xlsx)
              </Button>
              <div className="ml-auto flex items-end gap-3">
                <Field label="Libellé de l'analyse">
                  <TextInput
                    value={saveLabel}
                    onChange={(e) => setSaveLabel(e.target.value)}
                    placeholder="ex : Comparables HVAC — mission X"
                  />
                </Field>
                <Button variant="outline" onClick={saveRun}>
                  Enregistrer
                </Button>
              </div>
              {savedId != null && (
                <p className="w-full text-right text-xs text-ok">
                  Analyse n° {savedId} enregistrée — visible dans l&apos;Historique.
                </p>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
