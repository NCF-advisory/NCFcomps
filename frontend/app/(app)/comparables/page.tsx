"use client";

/** Module I — Comparables boursiers : bêtas (régression, désendetté) + multiples.
 *
 * Le job tourne côté backend (progression par société) ; l'exclusion d'un comparable
 * recalcule les stats via /api/comparables/stats sans aucun re-téléchargement.
 */

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  type BetaSummary,
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
  Disclosure,
  ErrorNote,
  Field,
  JobProgress,
  PageTitle,
  Select,
  StatCard,
  TextArea,
  TextInput,
  Th,
} from "@/components/ui";

type Mode = "tickers" | "noms";

const COLUMNS: {
  key: keyof CompanyRecord;
  label: string;
  fmt: (v: never) => string;
  align?: "left";
  tip?: string;
  groupStart?: boolean; // première colonne d'une famille -> filet vertical
  qualityBound?: boolean; // dérivé de la régression : ambre + hors stats si R² < seuil
}[] = [
  { key: "name", label: "Société", fmt: (v: string | null) => v ?? ND, align: "left" },
  { key: "market_cap", label: "Capi (M)", fmt: fmtMillions, groupStart: true,
    tip: "Capitalisation boursière, en millions, devise locale (indiquée à côté du ticker)" },
  { key: "net_debt", label: "Dette nette (M)", fmt: fmtMillions,
    tip: "Dette financière totale − trésorerie, en millions" },
  { key: "enterprise_value", label: "VE (M)", fmt: fmtMillions,
    tip: "Valeur d'entreprise = capitalisation + dette nette" },
  { key: "beta_source", label: "β publié", fmt: fmtBeta, groupStart: true,
    tip: "Bêta publié par Yahoo Finance (donné à titre de recoupement)" },
  { key: "beta_regression", label: "β régr.", fmt: fmtBeta, qualityBound: true,
    tip: "Bêta estimé par régression des rendements contre l'indice de la place de cotation" },
  { key: "r2", label: "R²", fmt: fmtBeta, qualityBound: true,
    tip: "Qualité d'ajustement de la régression, de 0 à 1 : faible R² = bêta peu fiable" },
  { key: "n_obs", label: "N pts", fmt: (v: number | null) => (v == null ? ND : String(v)),
    tip: "Nombre de points utilisés dans la régression" },
  { key: "gearing", label: "Gearing", fmt: (v: number | null) => fmtPct(v),
    tip: "Dette nette / capitalisation (D/E, en valeur de marché)" },
  { key: "beta_unlevered", label: "β désend.", fmt: fmtBeta, qualityBound: true,
    tip: "Bêta désendetté (Hamada) : β / (1 + (1 − IS) × D/E)" },
  { key: "ev_sales", label: "VE/CA", fmt: fmtMult, groupStart: true,
    tip: "Valeur d'entreprise / chiffre d'affaires" },
  { key: "ev_ebitda", label: "VE/EBITDA", fmt: fmtMult,
    tip: "Valeur d'entreprise / EBITDA" },
  { key: "ev_ebit", label: "VE/EBIT", fmt: fmtMult,
    tip: "Valeur d'entreprise / EBIT (résultat d'exploitation)" },
  { key: "pe_trailing", label: "PER", fmt: fmtMult,
    tip: "Cours / bénéfice net par action (12 derniers mois)" },
  { key: "pb", label: "P/B", fmt: fmtMult,
    tip: "Cours / actif net comptable par action" },
];

// Bandeau de regroupement au-dessus des en-têtes (la somme des spans = nb total de colonnes).
const GROUPS = [
  { label: "", span: 3 },                            // sélection + ticker + société
  { label: "Taille (M, devise locale)", span: 3 },
  { label: "Bêtas & structure", span: 6 },
  { label: "Multiples", span: 5 },
  { label: "", span: 1 },                            // couverture
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
  const [betaSummary, setBetaSummary] = useState<BetaSummary | null>(null);
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
          setBetaSummary(res.beta_summary);
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
    setBetaSummary(null);
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
      setError("Échec du lancement : le backend est-il démarré ?");
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
  const minR2 = betaSummary?.min_r2 ?? 0.1;
  // Régression trop faible : bêta affiché (en ambre) mais exclu des stats et de la synthèse.
  const isLowR2 = (r: CompanyRecord) =>
    r.beta_regression != null && (r.r2 == null || r.r2 < minR2);

  return (
    <div>
      <PageTitle
        kicker="Module I"
        title="Comparables boursiers"
        lede="Saisir un échantillon de sociétés cotées : l'outil calcule bêtas et multiples,
        affiche les statistiques de l'échantillon, puis exporte en Excel ou enregistre l'analyse."
      />
      <Disclosure summary="Méthode & sources">
        <p>
          <strong className="text-ink">Source : Yahoo Finance</strong> (gratuite) : multiples non
          retraités, à utiliser avec le jugement d&apos;un analyste.
        </p>
        <p>
          Le <strong className="text-ink">bêta de régression</strong> est estimé sur les rendements
          (période et fréquence choisies) contre l&apos;indice de la place de cotation ; R² et nombre
          de points mesurent sa fiabilité. Le <strong className="text-ink">bêta désendetté</strong>{" "}
          suit la formule de Hamada avec le taux d&apos;IS saisi.
        </p>
        <p>
          Montants en millions, <strong className="text-ink">devise locale</strong> indiquée par
          ligne ; bêtas et multiples restent comparables d&apos;un pays à l&apos;autre (ratios
          même-devise).
        </p>
      </Disclosure>

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
                  ? "Suffixes : .PA Paris, .AS Amsterdam, .L Londres, .SW Suisse, .VI Vienne, .DE Francfort, .MI Milan ; sans suffixe : USA."
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
            <Field
              label="Fréquence"
              hint={
                frequency === "1mo" && (period === "2y" || period === "3y")
                  ? "⚠ 2–3 ans en mensuel = trop peu de points (2 ans → 23 < seuil de 24) : préférer l'hebdomadaire."
                  : frequency === "1wk"
                    ? "Seuil : 52 points hebdo (~1 an de cotation minimum)."
                    : undefined
              }
            >
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
            <Card className="rise-in">
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-3">
                <h2 className="label-caps text-ink-mut">
                  Échantillon : {records.length} sociétés, {selection.length} retenues
                </h2>
                <div className="text-right text-xs text-ink-mut">
                  <p>
                    Décocher une ligne l&apos;exclut des statistiques (bas de tableau) et de
                    l&apos;export (recalcul immédiat).
                  </p>
                  <p>
                    <span className="font-medium text-warn">En ambre</span> : R² &lt;{" "}
                    {minR2.toLocaleString("fr-FR")}, bêta affiché mais exclu des statistiques
                    et de la synthèse.
                  </p>
                </div>
              </div>
              <div className="overflow-x-auto border-t border-hairline">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-paper-deep/60">
                    {GROUPS.map((g, i) => (
                      <th
                        key={i}
                        colSpan={g.span}
                        className={`px-3 pt-2 pb-1 text-center text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-ink-mut/70 ${
                          g.label ? "border-l border-hairline" : ""
                        }`}
                      >
                        {g.label}
                      </th>
                    ))}
                  </tr>
                  <tr className="border-b-2 border-ink bg-paper-deep text-left">
                    <Th left tip="Cocher = la société compte dans les statistiques et l'export">
                      Retenu
                    </Th>
                    <Th left>Ticker</Th>
                    {COLUMNS.map((c) => (
                      <Th
                        key={c.key}
                        left={c.align === "left"}
                        tip={c.tip}
                        className={c.groupStart ? "border-l border-hairline" : ""}
                      >
                        {c.label}
                      </Th>
                    ))}
                    <Th left tip="Couverture des données Yahoo : ok, partielle ou vide">
                      Couv.
                    </Th>
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
                            aria-label={`Retenir ${r.ticker} dans l'échantillon`}
                            className="size-4 cursor-pointer accent-[var(--color-brass)]"
                          />
                        </td>
                        <td className="tabular px-3 py-2 font-medium whitespace-nowrap">
                          {r.ticker}
                          {r.currency && (
                            <span className="ml-1.5 text-[0.65rem] font-normal text-ink-mut">
                              {r.currency}
                            </span>
                          )}
                        </td>
                        {COLUMNS.map((c) => {
                          const lowBeta = c.qualityBound && isLowR2(r);
                          return (
                            <td
                              key={c.key}
                              title={lowBeta
                                ? `R² < ${minR2.toLocaleString("fr-FR")} : bêta affiché mais exclu des statistiques`
                                : undefined}
                              className={`px-3 py-2 whitespace-nowrap ${
                                c.align === "left" ? "" : "tabular text-right"
                              } ${off ? "line-through" : ""} ${
                                c.groupStart ? "border-l border-hairline" : ""
                              } ${lowBeta ? "font-medium text-warn" : ""}`}
                            >
                              {c.fmt(r[c.key] as never)}
                            </td>
                          );
                        })}
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
                            <td
                              key={c.key}
                              className={`tabular px-3 py-2 text-right font-medium ${
                                c.groupStart ? "border-l border-hairline" : ""
                              }`}
                            >
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
              </div>
            </Card>

            {/* ——— Synthèse bêta : moyens retenus, endetté / ajusté / désendetté ——— */}
            {betaSummary && betaSummary.mean_levered != null && (
              <section className="rise-in grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard
                  label="β endetté moyen retenu"
                  value={fmtBeta(betaSummary.mean_levered)}
                  note={`${betaSummary.n_retained} bêta(s) retenu(s) · ${betaSummary.n_excluded_low_r2} écarté(s) (R² < ${minR2.toLocaleString("fr-FR")}) · médiane ${fmtBeta(betaSummary.median_levered)}`}
                />
                <StatCard
                  label="β ajusté (Blume)"
                  value={fmtBeta(betaSummary.mean_adjusted)}
                  note="2/3 × β endetté moyen + 1/3 : convergence vers le bêta de marché (usage prospectif)."
                />
                <StatCard
                  label="β désendetté moyen retenu"
                  value={fmtBeta(betaSummary.mean_unlevered)}
                  note={`Hamada, IS ${taxRate} % : base de réendettement sur la cible.`}
                />
              </section>
            )}

            {/* ——— Actions ——— */}
            <Card className="rise-in flex flex-wrap items-start gap-x-10 gap-y-4 p-5">
              <div>
                <Button onClick={exportSelection} busy={busyExport}>
                  Exporter la sélection (.xlsx)
                </Button>
                <p className="mt-1.5 text-xs text-ink-mut">
                  Fichier Excel formaté : uniquement les {selection.length} sociétés retenues.
                </p>
              </div>
              <div className="ml-auto flex items-end gap-3">
                <Field
                  label="Libellé de l'analyse"
                  hint="L'enregistrement alimente l'Historique et la Base sectorielle."
                >
                  <TextInput
                    value={saveLabel}
                    onChange={(e) => setSaveLabel(e.target.value)}
                    placeholder="ex : Comparables HVAC, mission X"
                  />
                </Field>
                <Button variant="outline" onClick={saveRun}>
                  Enregistrer
                </Button>
              </div>
              {savedId != null && (
                <p className="w-full text-right text-xs text-ok">
                  Analyse n° {savedId} enregistrée :{" "}
                  <Link href="/historique" className="underline underline-offset-2 hover:text-ink">
                    la consulter dans l&apos;Historique
                  </Link>
                  .
                </p>
              )}
            </Card>
          </>
        )}

        {done && records.length === 0 && (
          <Card className="p-6 text-sm text-ink-mut">
            Aucune donnée récupérée pour ces tickers : vérifier l&apos;orthographe et les suffixes
            de place (ex : <span className="tabular">AIR.PA</span> pour Airbus à Paris).
          </Card>
        )}
      </div>
    </div>
  );
}
