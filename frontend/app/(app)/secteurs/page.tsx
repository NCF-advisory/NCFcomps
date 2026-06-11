"use client";

/** Module III — Base sectorielle : bêtas et multiples déjà utilisés, agrégés par secteur.
 *
 * Lecture seule, alimentée automatiquement par les analyses enregistrées (Historique).
 * Médiane + fourchette interquartile [Q1–Q3] par secteur ; détail société par société. */

import { useCallback, useEffect, useState } from "react";

import {
  api,
  type MetricStat,
  type SectorAggregate,
  type SectorRecord,
} from "@/lib/api";
import { fmtBeta, fmtDate, fmtMult, ND } from "@/lib/format";
import { Card, ErrorNote, PageTitle, Spinner, TextInput } from "@/components/ui";

export default function SecteursPage() {
  const [sectors, setSectors] = useState<SectorAggregate[] | null>(null);
  const [filter, setFilter] = useState("");
  const [openSector, setOpenSector] = useState<string | null>(null);
  const [detail, setDetail] = useState<SectorRecord[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api
      .listSectors()
      .then((res) => setSectors(res.sectors))
      .catch(() => setError("Chargement impossible — le backend est-il démarré ?"));
  }, []);

  useEffect(refresh, [refresh]);

  async function toggle(sector: string) {
    if (openSector === sector) {
      setOpenSector(null);
      return;
    }
    setOpenSector(sector);
    setLoadingDetail(true);
    try {
      const res = await api.sectorDetail(sector);
      setDetail(res.records);
    } catch {
      setError("Détail du secteur indisponible.");
      setDetail([]);
    } finally {
      setLoadingDetail(false);
    }
  }

  const q = filter.trim().toLowerCase();
  const shown = (sectors ?? []).filter((s) => !q || s.sector.toLowerCase().includes(q));

  return (
    <div>
      <PageTitle
        kicker="Module III"
        title="Base sectorielle"
        lede="Bêtas désendettés et multiples déjà utilisés, agrégés par secteur à partir des
        analyses enregistrées. Médiane et fourchette interquartile [Q1–Q3] ; cliquer un secteur
        pour retrouver les valeurs société par société."
      />

      <ErrorNote message={error} />

      {sectors === null && <p className="text-sm text-ink-mut">Chargement…</p>}
      {sectors?.length === 0 && (
        <Card className="p-6 text-sm text-ink-mut">
          Aucune donnée sectorielle — la base se remplit dès qu&apos;une analyse est
          enregistrée (module Comparables → « Enregistrer »).
        </Card>
      )}

      {sectors && sectors.length > 0 && (
        <>
          <div className="mb-4 max-w-xs">
            <TextInput
              placeholder="Filtrer un secteur…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <Card className="rise-in overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink bg-paper-deep text-left">
                  <Th left>Secteur</Th>
                  <Th>Sociétés</Th>
                  <Th>β désend.</Th>
                  <Th>VE/EBITDA</Th>
                  <Th>VE/CA</Th>
                  <Th>PER</Th>
                  <Th left>Dern. util.</Th>
                </tr>
              </thead>
              <tbody>
                {shown.map((s) => {
                  const open = openSector === s.sector;
                  return (
                    <FragmentRow
                      key={s.sector}
                      s={s}
                      open={open}
                      onToggle={() => toggle(s.sector)}
                      detail={detail}
                      loadingDetail={loadingDetail}
                    />
                  );
                })}
                {shown.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-4 text-center text-ink-mut">
                      Aucun secteur ne correspond à « {filter} ».
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

function FragmentRow({
  s,
  open,
  onToggle,
  detail,
  loadingDetail,
}: {
  s: SectorAggregate;
  open: boolean;
  onToggle: () => void;
  detail: SectorRecord[];
  loadingDetail: boolean;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className={`cursor-pointer border-b border-hairline hover:bg-paper-deep/50 ${
          open ? "bg-paper-deep/40" : ""
        }`}
      >
        <td className="px-3 py-2 font-medium">
          <span className="mr-2 text-brass">{open ? "▾" : "▸"}</span>
          {s.sector}
        </td>
        <td className="tabular px-3 py-2 text-right">
          {s.n_companies}
          <span className="ml-1 text-[0.7rem] text-ink-mut">({s.n_records} pts)</span>
        </td>
        <MetricCell stat={s.metrics.beta_unlevered} kind="beta" />
        <MetricCell stat={s.metrics.ev_ebitda} kind="mult" />
        <MetricCell stat={s.metrics.ev_sales} kind="mult" />
        <MetricCell stat={s.metrics.pe_trailing} kind="mult" />
        <td className="tabular px-3 py-2 text-xs text-ink-mut whitespace-nowrap">
          {fmtDate(s.last_used)}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} className="border-b border-hairline bg-paper-deep/20 p-0">
            {loadingDetail ? (
              <div className="flex items-center gap-2 px-4 py-3 text-sm text-ink-mut">
                <Spinner /> Chargement du détail…
              </div>
            ) : (
              <DetailTable records={detail} />
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function DetailTable({ records }: { records: SectorRecord[] }) {
  if (records.length === 0) {
    return <p className="px-4 py-3 text-sm text-ink-mut">Aucune ligne.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-mut">
            <Th left>Ticker</Th>
            <Th left>Société</Th>
            <Th left>Pays</Th>
            <Th>β régr.</Th>
            <Th>β désend.</Th>
            <Th>VE/EBITDA</Th>
            <Th>VE/CA</Th>
            <Th>PER</Th>
            <Th left>Analyse</Th>
          </tr>
        </thead>
        <tbody>
          {records.map((r, i) => (
            <tr key={`${r.run_id}-${r.ticker}-${i}`} className="border-t border-hairline">
              <td className="tabular px-3 py-1.5 font-medium">{r.ticker ?? ND}</td>
              <td className="px-3 py-1.5">{r.name ?? ND}</td>
              <td className="px-3 py-1.5 text-ink-mut">{r.country ?? ND}</td>
              <Td>{fmtBeta(r.beta_regression)}</Td>
              <Td>{fmtBeta(r.beta_unlevered)}</Td>
              <Td>{fmtMult(r.ev_ebitda)}</Td>
              <Td>{fmtMult(r.ev_sales)}</Td>
              <Td>{fmtMult(r.pe_trailing)}</Td>
              <td className="px-3 py-1.5 text-xs text-ink-mut whitespace-nowrap">
                {r.label || `n° ${r.run_id}`} · {fmtDate(r.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricCell({ stat, kind }: { stat?: MetricStat; kind: "beta" | "mult" }) {
  if (!stat) return <td className="tabular px-3 py-2 text-right text-ink-mut">{ND}</td>;
  const fmt = kind === "beta" ? fmtBeta : fmtMult;
  return (
    <td className="tabular px-3 py-2 text-right whitespace-nowrap">
      <div className="font-medium">{fmt(stat.median)}</div>
      <div className="text-[0.7rem] text-ink-mut">
        {fmt(stat.q1)}–{fmt(stat.q3)} · n{stat.n}
      </div>
    </td>
  );
}

function Th({ children, left }: { children: React.ReactNode; left?: boolean }) {
  return (
    <th className={`label-caps px-3 py-2.5 whitespace-nowrap text-ink-mut ${left ? "text-left" : "text-right"}`}>
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="tabular px-3 py-1.5 text-right whitespace-nowrap">{children}</td>;
}
