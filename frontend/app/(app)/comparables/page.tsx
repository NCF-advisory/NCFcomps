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
  type DamodaranIndustry,
  downloadExcel,
  pollJob,
  type StatsMap,
} from "@/lib/api";
import { fmtBeta, fmtMillions, fmtMult, fmtPct, ND } from "@/lib/format";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Disclosure,
  ErrorNote,
  Field,
  JobProgress,
  PageTitle,
  Select,
  StatCard,
  TableSkeleton,
  TextArea,
  TextInput,
  Th,
} from "@/components/ui";
import { TableShell, useSort } from "@/components/table";
import { toast } from "@/components/toast";

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
  { key: "beta_std_err", label: "± IC 95 %",
    fmt: (v: number | null) => (v == null ? ND : fmtBeta(1.96 * v)),
    tip: "Demi-largeur de l'intervalle de confiance à 95 % du β de régression (± 1,96 × écart-type OLS de la pente)" },
  { key: "r2", label: "R²", fmt: fmtBeta, qualityBound: true,
    tip: "Qualité d'ajustement de la régression, de 0 à 1 : faible R² = bêta peu fiable" },
  { key: "n_obs", label: "N pts", fmt: (v: number | null) => (v == null ? ND : String(v)),
    tip: "Nombre de points utilisés dans la régression" },
  { key: "gearing", label: "Gearing", fmt: (v: number | null) => fmtPct(v),
    tip: "Dette nette / capitalisation (D/E, en valeur de marché)" },
  { key: "beta_unlevered", label: "β désend.", fmt: fmtBeta, qualityBound: true,
    tip: "Bêta désendetté (Hamada) : β / (1 + (1 − IS) × D/E)" },
  { key: "beta_unlevered_adjusted", label: "β désend. ajusté", fmt: fmtBeta, qualityBound: true,
    tip: "Bêta désendetté ajusté vers le marché : 0,67 × β désend. + 0,33 × 1" },
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
  { label: "Bêtas & structure", span: 8 },
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
  const [frequency, setFrequency] = useState("1wk");
  const [floorNetDebt, setFloorNetDebt] = useState(false);

  const [job, setJob] = useState<ComparablesJob | null>(null);
  const [phase, setPhase] = useState<"idle" | "resolving" | "running">("idle");
  const [error, setError] = useState<string | null>(null);

  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [stats, setStats] = useState<StatsMap | null>(null);
  const [betaSummary, setBetaSummary] = useState<BetaSummary | null>(null);
  const [damList, setDamList] = useState<DamodaranIndustry[]>([]);
  const [damAsOf, setDamAsOf] = useState<string | null>(null);
  const [damIndustry, setDamIndustry] = useState<string>("");
  const [statsN, setStatsN] = useState(0);
  const [saveLabel, setSaveLabel] = useState("");
  const [exportLibelle, setExportLibelle] = useState("");
  const [savedId, setSavedId] = useState<number | null>(null);
  const [busyExport, setBusyExport] = useState(false);
  const statsTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const records = useMemo(() => job?.records ?? [], [job]);
  const { sorted, toggle: toggleSort, dirFor } = useSort(records);
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

  // Référentiel Damodaran (étalon sectoriel) — chargé une fois.
  useEffect(() => {
    api
      .damodaranIndustries()
      .then((r) => {
        setDamList(r.industries);
        setDamAsOf(r.as_of);
      })
      .catch(() => undefined);
  }, []);

  // Présélection de l'industrie Damodaran suggérée à chaque nouveau résultat.
  useEffect(() => {
    const s = job?.damodaran?.suggested_industry;
    if (s) setDamIndustry(s);
  }, [job?.damodaran?.suggested_industry]);

  // Lance le calcul pour une liste de tickers déjà arrêtée.
  async function runTickers(tickers: string[]) {
    try {
      setPhase("running");
      const created = await api.createComparablesJob({
        tickers,
        tax_rate: Number(taxRate) / 100,
        period,
        frequency,
        floor_net_debt: floorNetDebt,
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

  async function launch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSavedId(null);
    setExcluded(new Set());
    setStats(null);
    setBetaSummary(null);
    setJob(null);

    const lines = input.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) {
      setError("Saisir au moins une ligne.");
      return;
    }

    // Mode « tickers » : on lance directement.
    if (mode === "tickers") {
      await runTickers(lines);
      return;
    }

    // Mode « noms » : résolution AUTOMATIQUE (aucun choix laissé à l'utilisateur), puis
    // lancement. On ne notifie QUE les noms pour lesquels aucun ticker n'a été trouvé.
    let tickers: string[] = [];
    try {
      setPhase("resolving");
      const res = await api.resolveNames(lines);
      tickers = res.results.filter((r) => r.match).map((r) => r.match!.symbol);
      const missing = res.results.filter((r) => !r.match).map((r) => r.query);
      if (missing.length > 0) {
        const msg = `Ticker introuvable — ${missing.length === 1 ? "société ignorée" : "sociétés ignorées"} : ${missing.join(", ")}. Saisis-le(s) directement en mode « Tickers ».`;
        setError(msg);
        toast(msg, "alert");
      }
    } catch {
      setError("Échec de la résolution : le backend est-il démarré ?");
      setPhase("idle");
      return;
    }
    if (tickers.length === 0) {
      setPhase("idle");
      return;
    }
    await runTickers(tickers);
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
      await downloadExcel(selection, exportLibelle);
      toast(`Export Excel téléchargé (${selection.length} sociétés).`);
    } catch {
      toast("Export impossible.", "alert");
    } finally {
      setBusyExport(false);
    }
  }

  async function saveRun() {
    try {
      const res = await api.saveRun(selection, saveLabel || undefined, job?.params);
      setSavedId(res.id);
      toast(`Analyse n° ${res.id} enregistrée.`);
    } catch {
      toast("Sauvegarde impossible.", "alert");
    }
  }

  const done = job?.status === "done";
  const minR2 = betaSummary?.min_r2 ?? 0.1;
  // Seuil d'illiquidité (part de rendements nuls) : serveur si dispo, sinon repli = settings.
  const maxZeroShare = betaSummary?.max_zero_share ?? 0.15;
  // Régression trop faible : bêta affiché (en ambre) mais exclu des stats et de la synthèse.
  const isLowR2 = (r: CompanyRecord) =>
    r.beta_regression != null && (r.r2 == null || r.r2 < minR2);
  // Titre peu liquide : trop de périodes sans variation de cours -> bêta OLS biaisé vers le bas.
  const isIlliquid = (r: CompanyRecord) =>
    r.zero_return_share != null && r.zero_return_share > maxZeroShare;
  // Fenêtre effective de régression (AAAA-MM) : une IPO récente peut afficher un « 5 ans » court.
  const shortMonth = (iso: string | null) => (iso ? iso.slice(0, 7) : "");

  // Comparaison Damodaran : β désendetté de l'échantillon (médiane retenue) vs secteur.
  const damSelected = damList.find((d) => d.industry === damIndustry) ?? null;
  const sampleUnlevMed = stats?.beta_unlevered?.median ?? null;
  const sampleUnlevMean = betaSummary?.mean_unlevered ?? null;
  // β ajusté : simple repère, HORS écart (Damodaran publie un bêta brut, cf. méthodo).
  const sampleAdjusted = betaSummary?.mean_unlevered_adjusted ?? null;
  const damGap =
    damSelected?.unlevered_beta != null && sampleUnlevMed != null
      ? (sampleUnlevMed - damSelected.unlevered_beta) / damSelected.unlevered_beta
      : null;

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
            <label className="flex cursor-pointer items-start gap-2 text-sm text-ink">
              <Checkbox
                checked={floorNetDebt}
                onChange={() => setFloorNetDebt((v) => !v)}
                className="mt-0.5"
                aria-label="Plancher la dette nette à 0 dans le désendettement"
              />
              <span
                title="Sociétés en trésorerie nette (dette nette < 0) : sans plancher, le désendettement (Hamada) ressort un β désendetté SUPÉRIEUR au β endetté. Cochée, la dette nette est bornée à 0 pour le seul désendettement (β désend. = β endetté) ; le gearing affiché reste le vrai gearing négatif."
              >
                Plancher la dette nette à 0 (sociétés en trésorerie nette)
              </span>
            </label>
            <Button type="submit" busy={phase !== "idle"}>
              {phase === "resolving" ? "Résolution…" : "Lancer le calcul"}
            </Button>
          </div>
        </form>

      </Card>

      <div className="mt-6 space-y-6">
        <ErrorNote message={error} />

        {job && job.status !== "done" && job.status !== "error" && (
          <Card className="overflow-hidden">
            <div className="p-6 pb-2">
              <JobProgress
                progress={job.progress}
                total={job.total}
                label="Sociétés traitées"
              />
            </div>
            <TableSkeleton rows={Math.min(8, Math.max(3, job.total))} cols={9} />
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
              <TableShell className="overflow-hidden rounded-b-[13px] border-t border-hairline">
              <table className="table-fin text-sm">
                <thead>
                  <tr className="th-band">
                    {/* Rail : 2 cellules (colSpan 2 + colonne Société) pour un bord exact */}
                    <th colSpan={2} className="stick [--stick-l:0px]" />
                    <th className="stick stick-end [--stick-l:158px]" />
                    {GROUPS.slice(1).map((g, i) => (
                      <th
                        key={i}
                        colSpan={g.span}
                        className={`px-3 text-center text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-ink-mut/70 ${
                          g.label ? "border-l border-hairline" : ""
                        }`}
                      >
                        {g.label}
                      </th>
                    ))}
                  </tr>
                  <tr className="th-cols text-left">
                    <Th
                      left
                      tip="Cocher = la société compte dans les statistiques et l'export"
                      className="stick w-12 [--stick-l:0px]"
                    >
                      <span aria-hidden>✓</span>
                      <span className="sr-only">Retenu</span>
                    </Th>
                    <Th
                      left
                      className="stick w-[110px] [--stick-l:48px]"
                      onSort={() => toggleSort("ticker")}
                      sortDir={dirFor("ticker")}
                    >
                      Ticker
                    </Th>
                    {COLUMNS.map((c) => (
                      <Th
                        key={c.key}
                        left={c.align === "left"}
                        tip={c.tip}
                        onSort={() => toggleSort(c.key)}
                        sortDir={dirFor(c.key)}
                        className={`${c.groupStart ? "border-l border-hairline" : ""} ${
                          c.key === "name" ? "stick stick-end [--stick-l:158px]" : ""
                        }`}
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
                  {sorted.map((r) => {
                    const off = excluded.has(r.ticker);
                    const cov = job.coverage?.[r.ticker] ?? "ok";
                    return (
                      <tr
                        key={r.ticker}
                        className={`transition-opacity hover:bg-paper-deep/50 ${
                          off ? "opacity-35" : ""
                        }`}
                      >
                        <td className="stick px-3 py-2 [--stick-l:0px]">
                          <Checkbox
                            checked={!off}
                            onChange={() => toggle(r.ticker)}
                            aria-label={`Retenir ${r.ticker} dans l'échantillon`}
                          />
                        </td>
                        <td className="tabular stick px-3 py-2 font-medium whitespace-nowrap [--stick-l:48px]">
                          {r.ticker}
                          {r.currency && (
                            <span className="ml-1.5 text-[0.65rem] font-normal text-ink-mut">
                              {r.currency}
                            </span>
                          )}
                        </td>
                        {COLUMNS.map((c) => {
                          const lowBeta = c.qualityBound && isLowR2(r);
                          const isName = c.key === "name";
                          // Signal d'illiquidité (soulignement pointillé ambre) sur « β régr. ».
                          const illiquid = c.key === "beta_regression" && isIlliquid(r);
                          // Infobulle « N pts » : fenêtre effectivement régressée (du … au …).
                          const windowTip =
                            c.key === "n_obs" && r.n_obs != null && r.beta_start && r.beta_end
                              ? `${r.n_obs} pts · du ${shortMonth(r.beta_start)} au ${shortMonth(r.beta_end)}`
                              : undefined;
                          const title = illiquid
                            ? `${Math.round((r.zero_return_share ?? 0) * 100)} % de périodes sans variation de cours : bêta possiblement sous-estimé (illiquidité).`
                            : windowTip
                              ? windowTip
                              : lowBeta
                                ? `R² < ${minR2.toLocaleString("fr-FR")} : bêta affiché mais exclu des statistiques`
                                : isName
                                  ? ((r.name as string | null) ?? undefined)
                                  : undefined;
                          return (
                            <td
                              key={c.key}
                              title={title}
                              className={`px-3 py-2 whitespace-nowrap ${
                                c.align === "left" ? "" : "tabular text-right"
                              } ${off ? "line-through" : ""} ${
                                c.groupStart ? "border-l border-hairline" : ""
                              } ${lowBeta ? "font-medium text-warn" : ""} ${
                                illiquid ? "cursor-help underline decoration-warn decoration-dotted underline-offset-4" : ""
                              } ${
                                windowTip ? "cursor-help" : ""
                              } ${
                                isName ? "stick stick-end max-w-[200px] truncate [--stick-l:158px]" : ""
                              }`}
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
                      <tr key={row.key}>
                        <td
                          colSpan={2}
                          className="label-caps stick px-3 py-2 whitespace-nowrap text-ink-mut [--stick-l:0px]"
                        >
                          {row.label}
                        </td>
                        <td className="tabular stick stick-end px-3 py-2 text-xs text-ink-mut [--stick-l:158px]">
                          {i === 0 ? `${statsN} retenues` : ""}
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
              </TableShell>
            </Card>

            {/* ——— Synthèse bêta : moyens retenus, endetté / désendetté / désendetté ajusté ——— */}
            {betaSummary && betaSummary.mean_levered != null && (
              <section className="rise-in grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard
                  label="β endetté moyen retenu"
                  value={fmtBeta(betaSummary.mean_levered)}
                  note={`${betaSummary.n_retained} bêta(s) retenu(s) · ${betaSummary.n_excluded_low_r2} écarté(s) (R² < ${minR2.toLocaleString("fr-FR")}) · médiane ${fmtBeta(betaSummary.median_levered)}`}
                />
                <StatCard
                  label="β désendetté moyen retenu"
                  value={fmtBeta(betaSummary.mean_unlevered)}
                  note={`Hamada, IS ${taxRate} % : base de réendettement sur la cible.`}
                />
                <StatCard
                  label="β désendetté ajusté"
                  value={fmtBeta(betaSummary.mean_unlevered_adjusted)}
                  note="0,67 × β désendetté moyen + 0,33 × 1 : convergence vers le bêta de marché (usage prospectif)."
                />
              </section>
            )}

            {/* ——— Comparaison sectorielle Damodaran (étalon de fiabilité) ——— */}
            {done && sampleUnlevMed != null && damList.length > 0 && (
              <Card className="rise-in p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="label-caps text-ink-mut">
                      Comparaison sectorielle — Damodaran (Global)
                    </p>
                    <p className="mt-1 text-xs text-ink-mut">
                      β désendetté de l&apos;échantillon vs secteur Damodaran
                      {damAsOf ? ` (au ${damAsOf})` : ""}.
                      {job?.damodaran?.suggested_industry
                        ? " Secteur déduit des sociétés ; ajustable."
                        : " Aucun secteur déduit : choisis-le."}
                    </p>
                  </div>
                  <div className="w-64 max-w-full">
                    <Select value={damIndustry} onChange={(e) => setDamIndustry(e.target.value)}>
                      {!damIndustry && <option value="">— choisir un secteur —</option>}
                      {damList.map((d) => (
                        <option key={d.industry} value={d.industry}>
                          {d.industry}
                        </option>
                      ))}
                    </Select>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <p className="label-caps text-ink-mut">β désend. — échantillon</p>
                    <p className="tabular mt-1 text-3xl font-extrabold text-ink-strong">
                      {fmtBeta(sampleUnlevMed)}
                    </p>
                    <p className="mt-1 text-xs text-ink-mut">
                      médiane retenue · moyenne {fmtBeta(sampleUnlevMean)}
                    </p>
                  </div>
                  <div>
                    <p className="label-caps text-ink-mut">β désend. — Damodaran</p>
                    <p className="tabular mt-1 text-3xl font-extrabold text-ink-strong">
                      {fmtBeta(damSelected?.unlevered_beta ?? null)}
                    </p>
                    <p className="mt-1 text-xs text-ink-mut">
                      {damSelected?.n_firms ? `${damSelected.n_firms} sociétés` : "—"} · corrigé cash{" "}
                      {fmtBeta(damSelected?.unlevered_beta_cash ?? null)}
                    </p>
                  </div>
                  <div>
                    <p className="label-caps text-ink-mut">Écart vs secteur</p>
                    <p
                      className="tabular mt-1 text-3xl font-extrabold"
                      style={{
                        color:
                          damGap == null
                            ? undefined
                            : Math.abs(damGap) <= 0.15
                              ? "#15803d"
                              : Math.abs(damGap) <= 0.3
                                ? "#B45309"
                                : "#b91c1c",
                      }}
                    >
                      {damGap == null ? ND : `${damGap > 0 ? "+" : ""}${(damGap * 100).toFixed(0)} %`}
                    </p>
                    <p className="mt-1 text-xs text-ink-mut">
                      {damGap == null
                        ? "—"
                        : Math.abs(damGap) <= 0.15
                          ? "cohérent avec le secteur"
                          : Math.abs(damGap) <= 0.3
                            ? "à surveiller"
                            : "écart important — à investiguer"}
                    </p>
                  </div>
                </div>

                <p className="mt-3 border-t border-hairline pt-2 text-xs text-ink-mut">
                  Pour mémoire — notre β désendetté <strong>ajusté</strong> (0,67·βu + 0,33) ={" "}
                  {fmtBeta(sampleAdjusted)}. Repère seulement : l&apos;écart se mesure en β{" "}
                  <strong>brut</strong>, car Damodaran publie un bêta de régression brut (non
                  ajusté) — comparer l&apos;ajusté au brut introduirait un biais vers 1.
                </p>
              </Card>
            )}

            {/* ——— Actions ——— */}
            <Card className="rise-in flex flex-wrap items-start gap-x-10 gap-y-4 p-5">
              <div className="flex items-end gap-3">
                <Field
                  label="Libellé de l'échantillon"
                  hint="En-tête du tableau « Données à retenir » de l'export."
                >
                  <TextInput
                    value={exportLibelle}
                    onChange={(e) => setExportLibelle(e.target.value)}
                    placeholder="ex : Acier, Software…"
                  />
                </Field>
                <div>
                  <Button onClick={exportSelection} busy={busyExport}>
                    Exporter la sélection (.xlsx)
                  </Button>
                  <p className="mt-1.5 text-xs text-ink-mut">
                    Fichier Excel formaté : uniquement les {selection.length} sociétés retenues.
                  </p>
                </div>
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
