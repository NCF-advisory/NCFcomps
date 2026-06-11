"use client";

/** Module III — Historique : analyses enregistrées (SQLite backend), consultation,
 * ré-export Excel, suppression. */

import { useCallback, useEffect, useState } from "react";

import {
  api,
  type Cession,
  type CompanyRecord,
  downloadRunExcel,
  type RunKind,
  type RunSummary,
} from "@/lib/api";
import { fmtBeta, fmtDate, fmtEuros, fmtMillions, fmtMult, fmtPct, ND } from "@/lib/format";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  PageTitle,
  TableSkeleton,
  Td,
  Th,
} from "@/components/ui";
import { TableShell } from "@/components/table";
import { toast } from "@/components/toast";

export default function HistoriquePage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [openKind, setOpenKind] = useState<RunKind>("comparables");
  const [records, setRecords] = useState<CompanyRecord[]>([]);
  const [cessions, setCessions] = useState<Cession[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api
      .listRuns()
      .then((res) => setRuns(res.runs))
      .catch(() => setError("Chargement impossible : le backend est-il démarré ?"));
  }, []);

  useEffect(refresh, [refresh]);

  async function open(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    try {
      const res = await api.getRun(id);
      setOpenKind(res.kind);
      setRecords(res.records ?? []);
      setCessions(res.cessions ?? []);
      setOpenId(id);
    } catch {
      setError("Analyse introuvable.");
    }
  }

  async function remove(id: number) {
    if (!window.confirm(`Supprimer définitivement l'analyse n° ${id} ?`)) return;
    try {
      await api.deleteRun(id);
      if (openId === id) setOpenId(null);
      toast(`Analyse n° ${id} supprimée.`);
      refresh();
    } catch {
      toast("Suppression impossible.", "alert");
    }
  }

  return (
    <div>
      <PageTitle
        kicker="Module IV"
        title="Historique des analyses"
        lede="Chaque analyse enregistrée fige l'échantillon et ses paramètres (IS, période,
        fréquence) à la date du calcul, utile pour tracer une valorisation dans le temps.
        Ces analyses alimentent aussi la Base sectorielle."
      />

      <ErrorNote message={error} />

      {runs === null && (
        <Card className="overflow-hidden">
          <TableSkeleton rows={3} cols={5} />
        </Card>
      )}
      {runs?.length === 0 && (
        <Card className="p-6 text-sm text-ink-mut">
          Aucune analyse enregistrée pour l&apos;instant : lancer un calcul dans le module
          Comparables puis « Enregistrer ».
        </Card>
      )}

      <div className="space-y-3">
        {runs?.map((run) => (
          <Card key={run.id} className="rise-in">
            <div className="flex flex-wrap items-center gap-4 p-4">
              <span className="tabular text-2xl font-extrabold tracking-[-0.02em] text-brass">
                {String(run.id).padStart(3, "0")}
              </span>
              <div className="min-w-48 flex-1">
                <p className="font-medium">
                  {run.label || "Analyse sans libellé"}
                  <span className="ml-2 align-middle">
                    <Badge tone={run.kind === "cessions" ? "warn" : "neutral"}>
                      {run.kind === "cessions" ? "Cessions FR" : "Comparables"}
                    </Badge>
                  </span>
                </p>
                <p className="tabular mt-0.5 text-xs text-ink-mut">
                  {new Date(run.created_at).toLocaleString("fr-FR")} · {run.username ?? "?"} ·{" "}
                  {run.n_records} sociétés
                  {typeof run.params?.tax_rate === "number" &&
                    ` · IS ${(run.params.tax_rate as number) * 100} %`}
                  {typeof run.params?.period === "string" && ` · ${run.params.period}`}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => open(run.id)}>
                  {openId === run.id ? "Refermer" : "Consulter"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadRunExcel(run.id, run.kind).catch(() =>
                      toast("Export impossible.", "alert"),
                    )
                  }
                >
                  .xlsx
                </Button>
                <Button variant="danger" onClick={() => remove(run.id)}>
                  Supprimer
                </Button>
              </div>
            </div>

            {openId === run.id && openKind === "cessions" && (
              <TableShell className="overflow-hidden rounded-b-[13px] border-t border-hairline">
                <table className="table-fin no-band text-sm">
                  <thead>
                    <tr className="th-cols text-left">
                      <Th left>Entreprise</Th>
                      <Th left>NAF</Th>
                      <Th left>Date</Th>
                      <Th>Prix</Th>
                      <Th>CA</Th>
                      <Th tip="EBE des comptes sociaux, proxy d'EBITDA">EBITDA</Th>
                      <Th>% CA</Th>
                      <Th>× EBITDA</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {cessions.map((c, i) => (
                      <tr key={`${c.siren}-${i}`} className="hover:bg-paper-deep/50">
                        <td className="max-w-[280px] truncate px-3 py-2" title={c.nom ?? undefined}>
                          {c.nom ?? ND}
                        </td>
                        <td className="tabular px-3 py-2">{c.naf ?? ND}</td>
                        <td className="tabular px-3 py-2 whitespace-nowrap">{fmtDate(c.date)}</td>
                        <Td>{fmtEuros(c.prix)}</Td>
                        <Td>{fmtEuros(c.ca)}</Td>
                        <Td>{fmtEuros(c.ebe)}</Td>
                        <Td>{c.pct_ca != null ? fmtPct(c.pct_ca, 0) : ND}</Td>
                        <Td>{fmtMult(c.mult_ebe)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableShell>
            )}

            {openId === run.id && openKind === "comparables" && (
              <TableShell className="overflow-hidden rounded-b-[13px] border-t border-hairline">
                <table className="table-fin no-band text-sm">
                  <thead>
                    <tr className="th-cols text-left">
                      <Th left>Ticker</Th>
                      <Th left>Société</Th>
                      <Th tip="Capitalisation boursière, en millions (devise locale)">Capi (M)</Th>
                      <Th tip="Valeur d'entreprise = capitalisation + dette nette">VE (M)</Th>
                      <Th tip="Bêta de régression contre l'indice de la place de cotation">β régr.</Th>
                      <Th tip="Qualité d'ajustement de la régression (0 à 1)">R²</Th>
                      <Th tip="Dette nette / capitalisation (D/E)">Gearing</Th>
                      <Th tip="Bêta désendetté (Hamada)">β désend.</Th>
                      <Th>VE/CA</Th>
                      <Th>VE/EBITDA</Th>
                      <Th>PER</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r) => (
                      <tr key={r.ticker} className="hover:bg-paper-deep/50">
                        <td className="tabular px-3 py-2 font-medium">{r.ticker}</td>
                        <td className="px-3 py-2">{r.name ?? ND}</td>
                        <Td>{fmtMillions(r.market_cap)}</Td>
                        <Td>{fmtMillions(r.enterprise_value)}</Td>
                        <Td>{fmtBeta(r.beta_regression)}</Td>
                        <Td>{fmtBeta(r.r2)}</Td>
                        <Td>{fmtPct(r.gearing)}</Td>
                        <Td>{fmtBeta(r.beta_unlevered)}</Td>
                        <Td>{fmtMult(r.ev_sales)}</Td>
                        <Td>{fmtMult(r.ev_ebitda)}</Td>
                        <Td>{fmtMult(r.pe_trailing)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableShell>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

