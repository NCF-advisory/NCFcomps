"use client";

/** Module II — Cessions de fonds de commerce (France) : % du CA et multiple d'EBITDA.
 *
 * Métrique de marge = EBE des comptes sociaux, utilisé comme proxy d'EBITDA (champ
 * interne `ebe`/`mult_ebe`, affiché « EBITDA »). Sources publiques gratuites : BODACC
 * (prix), ratios INPI/BCE (CA, EBE), Recherche d'entreprises (NAF). Couverture
 * partielle : comptes confidentiels (~45 %) exclus.
 */

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  type CessionsJob,
  type CessionsSummary,
  downloadCessionsExcel,
  pollJob,
} from "@/lib/api";
import { fmtDate, fmtEuros, fmtMult, fmtPct, ND } from "@/lib/format";
import {
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
  TextInput,
  Th,
} from "@/components/ui";
import { TableShell, useSort } from "@/components/table";
import { toast } from "@/components/toast";

export default function CessionsPage() {
  const [contains, setContains] = useState("");
  const [departement, setDepartement] = useState("");
  const [years, setYears] = useState("10");
  const [limit, setLimit] = useState("50");
  const [requireCa, setRequireCa] = useState("oui");

  const [job, setJob] = useState<CessionsJob | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sélection « Retenu » (indices dans job.cessions) + agrégats recalculés en direct.
  const [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [summary, setSummary] = useState<CessionsSummary | null>(null);
  const [saveLabel, setSaveLabel] = useState("");
  const [savedId, setSavedId] = useState<number | null>(null);
  const [busyExport, setBusyExport] = useState(false);
  const statsTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function launch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setJob(null);
    setRunning(true);
    try {
      let since = "2008-01-01";             // le BODACC ne publie pas avant 2008
      if (years !== "tout") {
        const d = new Date();
        d.setFullYear(d.getFullYear() - Number(years));
        since = d.toISOString().slice(0, 10);
      }
      const created = await api.createCessionsJob({
        contains: contains.trim() || undefined,
        departement: departement.trim() || undefined,
        since,
        limit: Number(limit),
        require_ca: requireCa === "oui",
      });
      setJob(created);
      const finished = await pollJob(() => api.cessionsJob(created.id), setJob);
      if (finished.status === "error") setError(finished.error ?? "Échec de la recherche.");
    } catch {
      setError("Échec du lancement : le backend est-il démarré ?");
    } finally {
      setRunning(false);
    }
  }

  const done = job?.status === "done";
  const cessions = useMemo(() => job?.cessions ?? [], [job]);
  const selection = useMemo(
    () => cessions.filter((_, i) => !excluded.has(i)),
    [cessions, excluded],
  );
  // Tri sur des lignes indexées : l'index d'origine reste la clé de sélection.
  const rows = useMemo(() => cessions.map((c, i) => ({ ...c, _idx: i })), [cessions]);
  const overall = summary?.overall;
  const bareme = useMemo(() => summary?.by_activite ?? [], [summary]);
  const sortBareme = useSort(bareme);
  const sortDetail = useSort(rows);

  // À la fin du job : sélection par défaut (règle d'or) renvoyée par l'API.
  useEffect(() => {
    if (job?.status !== "done") return;
    const def = job.retenu_defaut ?? [];
    setExcluded(new Set(def.flatMap((ok, i) => (ok ? [] : [i]))));
    setSummary(job.summary ?? null);
    setSavedId(null);
  }, [job]);

  // Agrégats recalculés (débouncés) à chaque changement de sélection — zéro re-fetch.
  useEffect(() => {
    if (job?.status !== "done" || selection.length === 0) return;
    if (statsTimer.current) clearTimeout(statsTimer.current);
    statsTimer.current = setTimeout(() => {
      api
        .cessionsStats(selection)
        .then((res) => setSummary(res.summary))
        .catch(() => undefined);
    }, 250);
    return () => {
      if (statsTimer.current) clearTimeout(statsTimer.current);
    };
  }, [selection, job]);

  function toggleRetenu(idx: number) {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  async function exportSelection() {
    setBusyExport(true);
    try {
      await downloadCessionsExcel(selection);
      toast(`Export Excel téléchargé (${selection.length} cessions).`);
    } catch {
      toast("Export impossible.", "alert");
    } finally {
      setBusyExport(false);
    }
  }

  async function saveSelection() {
    try {
      const res = await api.saveCessionsRun(selection, saveLabel || undefined, job?.params);
      setSavedId(res.id);
      toast(`Recherche n° ${res.id} enregistrée.`);
    } catch {
      toast("Sauvegarde impossible.", "alert");
    }
  }

  return (
    <div>
      <PageTitle
        kicker="Module II"
        title="Cessions de fonds de commerce (France)"
        lede="Rechercher les cessions publiées au BODACC par activité ou département : l'outil
        rapproche chaque prix du CA et de l'EBITDA de la société cédante, puis en tire un barème
        par activité."
      />
      <Disclosure summary="Méthode & sources">
        <p>
          <strong className="text-ink">Sources publiques gratuites</strong> : BODACC (prix de
          cession), ratios INPI/Banque de France et comptes déposés à l&apos;INPI (CA, EBE),
          exercice clos précédant la cession.
        </p>
        <p>
          L&apos;<strong className="text-ink">EBITDA est approché par l&apos;EBE</strong> des
          comptes sociaux (convention Banque de France). Médianes robustes : ratios retenus entre
          5–400 % du CA et 0,5–15× l&apos;EBITDA, extrêmes exclus.
        </p>
        <p>
          <strong className="text-ink">Couverture partielle</strong> : les sociétés aux comptes
          confidentiels (~45 % des dépôts, art. L232-25) n&apos;ont pas de CA/EBE exploitable.
          Ordre de grandeur indicatif : chaque ligne est vérifiable (liens BODACC / Annuaire).
        </p>
      </Disclosure>

      {/* ——— Formulaire ——— */}
      <Card className="p-6">
        <form onSubmit={launch} className="grid grid-cols-2 items-start gap-4 md:grid-cols-6">
          <div className="col-span-2">
            <Field
              label="Activité (texte libre)"
              hint="ex : conseil en informatique, boulangerie, 62.02A — traduit en mots-clés + NAF"
            >
              <TextInput value={contains} onChange={(e) => setContains(e.target.value)} />
            </Field>
          </div>
          <Field label="Département" hint="vide = toute la France">
            <TextInput
              value={departement}
              onChange={(e) => setDepartement(e.target.value)}
              placeholder="75"
            />
          </Field>
          <Field label="Fenêtre">
            <Select value={years} onChange={(e) => setYears(e.target.value)}>
              <option value="3">3 ans</option>
              <option value="5">5 ans</option>
              <option value="10">10 ans</option>
              <option value="tout">Tout (depuis 2008)</option>
            </Select>
          </Field>
          <Field label="Cessions visées" hint="objectif de lignes exploitables (CA connu)">
            <Select value={limit} onChange={(e) => setLimit(e.target.value)}>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </Select>
          </Field>
          <Field label="CA requis" hint="exclure les comptes confidentiels (sans CA)">
            <Select value={requireCa} onChange={(e) => setRequireCa(e.target.value)}>
              <option value="oui">Oui</option>
              <option value="non">Non</option>
            </Select>
          </Field>
          <div className="col-span-2 flex justify-end md:col-span-6">
            <Button type="submit" busy={running}>
              Rechercher
            </Button>
          </div>
        </form>
      </Card>

      <div className="mt-6 space-y-6">
        <ErrorNote message={error} />

        {job && !done && job.status !== "error" && (
          <Card className="overflow-hidden">
            <div className="p-6 pb-2">
              <JobProgress
                progress={job.progress}
                total={job.total}
                label="Recherche BODACC + enrichissement INPI (peut prendre quelques minutes)"
              />
            </div>
            <TableSkeleton rows={6} cols={8} />
          </Card>
        )}

        {/* ——— Recherche interprétée + entonnoir ——— */}
        {done && job.search && (job.search.keywords.length > 0 || job.search.n_annonces > 0) && (
          <Card className="rise-in space-y-1 p-4 text-sm text-ink-mut">
            {job.search.keywords.length > 0 && (
              <p>
                <span className="font-medium text-ink">Recherche élargie</span> :{" "}
                {job.search.keywords.join(" ou ")}
                {job.search.naf_labels.length > 0 && (
                  <>
                    {" "}· activités ciblées (NAF) : {job.search.naf_labels.slice(0, 3).join(" ; ")}
                    {job.search.naf_codes.length > 3 && ` (+${job.search.naf_codes.length - 3})`}
                  </>
                )}
              </p>
            )}
            <p>
              {job.search.n_annonces} annonce{job.search.n_annonces > 1 ? "s" : ""} avec prix
              balayée{job.search.n_annonces > 1 ? "s" : ""}
              {job.search.n_naf_exclues > 0 && <> · {job.search.n_naf_exclues} hors activité</>}
              {job.search.n_sans_ca > 0 && (
                <> · {job.search.n_sans_ca} sans CA exploitable (comptes confidentiels)</>
              )}
              {" "}· <span className="font-medium text-ink">{job.cessions?.length ?? 0} retenue{(job.cessions?.length ?? 0) > 1 ? "s" : ""}</span>
            </p>
          </Card>
        )}

        {/* ——— Synthèse ——— */}
        {done && overall && (
          <section className="rise-in grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard
              label="Prix médian / CA"
              value={overall.median_pct_ca != null ? fmtPct(overall.median_pct_ca, 0) : ND}
              note={`${overall.n_plausible} ratios plausibles · ${overall.n_pct_outliers} extrêmes exclus`}
            />
            <StatCard
              label="Prix médian / EBITDA"
              value={overall.median_mult_ebe != null ? fmtMult(overall.median_mult_ebe) : ND}
              note={`${overall.n_avec_ebe} multiples retenus · ${overall.n_ebe_outliers} extrêmes exclus`}
            />
            <StatCard
              label="Prix médian de cession"
              value={overall.median_prix != null ? fmtEuros(overall.median_prix) : ND}
              note={`${overall.n_total} cessions avec CA connu`}
            />
          </section>
        )}

        {/* ——— Barème par activité ——— */}
        {done && bareme.length > 0 && (
          <Card className="rise-in overflow-hidden">
            <h2 className="label-caps border-b border-hairline px-4 py-3 text-ink-mut">
              Barème par activité (NAF) : médianes robustes
            </h2>
            <TableShell className="rounded-b-[13px]">
              <table className="table-fin no-band text-sm">
                <thead>
                  <tr className="th-cols text-left">
                    <Th left tip="Code d'activité principale (nomenclature NAF)"
                        onSort={() => sortBareme.toggle("naf")} sortDir={sortBareme.dirFor("naf")}>
                      NAF
                    </Th>
                    <Th tip="Nombre de cessions retenues dans l'activité"
                        onSort={() => sortBareme.toggle("n")} sortDir={sortBareme.dirFor("n")}>
                      n
                    </Th>
                    <Th tip="Médiane des prix de cession rapportés au CA"
                        onSort={() => sortBareme.toggle("median_pct_ca")}
                        sortDir={sortBareme.dirFor("median_pct_ca")}>
                      % du CA
                    </Th>
                    <Th tip="Médiane des prix rapportés à l'EBITDA (EBE des comptes sociaux)"
                        onSort={() => sortBareme.toggle("median_mult_ebe")}
                        sortDir={sortBareme.dirFor("median_mult_ebe")}>
                      × EBITDA
                    </Th>
                    <Th onSort={() => sortBareme.toggle("median_prix")}
                        sortDir={sortBareme.dirFor("median_prix")}>
                      Prix médian
                    </Th>
                    <Th onSort={() => sortBareme.toggle("median_ca")}
                        sortDir={sortBareme.dirFor("median_ca")}>
                      CA médian
                    </Th>
                  </tr>
                </thead>
                <tbody>
                  {sortBareme.sorted.map((g) => (
                    <tr key={g.naf} className="hover:bg-paper-deep/50">
                      <td className="tabular px-3 py-2 font-medium">{g.naf}</td>
                      <td className="tabular px-3 py-2 text-right">{g.n}</td>
                      <td className="tabular px-3 py-2 text-right">
                        {g.median_pct_ca != null ? fmtPct(g.median_pct_ca, 0) : ND}
                      </td>
                      <td className="tabular px-3 py-2 text-right">{fmtMult(g.median_mult_ebe)}</td>
                      <td className="tabular px-3 py-2 text-right">{fmtEuros(g.median_prix)}</td>
                      <td className="tabular px-3 py-2 text-right">{fmtEuros(g.median_ca)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          </Card>
        )}

        {/* ——— Détail des cessions ——— */}
        {done && cessions.length > 0 && (
          <Card className="rise-in overflow-hidden">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-hairline px-4 py-3">
              <h2 className="label-caps text-ink-mut">
                Détail des cessions : {cessions.length} trouvées, {selection.length} retenues
              </h2>
              <p className="text-xs text-ink-mut">
                Décocher une ligne l&apos;exclut des médianes, du barème et de l&apos;export
                (recalcul immédiat). Présélection : ratios plausibles hors extrêmes.
              </p>
            </div>
            <TableShell className="rounded-b-[13px]">
              <table className="table-fin no-band text-sm">
                <thead>
                  <tr className="th-cols text-left">
                    <Th
                      left
                      tip="Cocher = la cession compte dans les médianes et l'export"
                      className="stick w-12 [--stick-l:0px]"
                    >
                      <span aria-hidden>✓</span>
                      <span className="sr-only">Retenu</span>
                    </Th>
                    <Th left className="stick stick-end [--stick-l:48px]"
                        onSort={() => sortDetail.toggle("nom")} sortDir={sortDetail.dirFor("nom")}>
                      Entreprise
                    </Th>
                    <Th left onSort={() => sortDetail.toggle("ville")} sortDir={sortDetail.dirFor("ville")}>
                      Lieu
                    </Th>
                    <Th left onSort={() => sortDetail.toggle("date")} sortDir={sortDetail.dirFor("date")}>
                      Date
                    </Th>
                    <Th tip="Prix de cession publié au BODACC"
                        onSort={() => sortDetail.toggle("prix")} sortDir={sortDetail.dirFor("prix")}>
                      Prix
                    </Th>
                    <Th tip="Chiffre d'affaires du dernier exercice clos avant la cession"
                        onSort={() => sortDetail.toggle("ca")} sortDir={sortDetail.dirFor("ca")}>
                      CA (exercice)
                    </Th>
                    <Th tip="EBE des comptes sociaux, proxy d'EBITDA"
                        onSort={() => sortDetail.toggle("ebe")} sortDir={sortDetail.dirFor("ebe")}>
                      EBITDA
                    </Th>
                    <Th tip="Prix de cession / CA"
                        onSort={() => sortDetail.toggle("pct_ca")} sortDir={sortDetail.dirFor("pct_ca")}>
                      % CA
                    </Th>
                    <Th tip="Prix de cession / EBITDA"
                        onSort={() => sortDetail.toggle("mult_ebe")} sortDir={sortDetail.dirFor("mult_ebe")}>
                      × EBITDA
                    </Th>
                    <Th left tip="Sources officielles pour contrôler la ligne">Vérifier</Th>
                  </tr>
                </thead>
                <tbody>
                  {sortDetail.sorted.map((c) => {
                    const off = excluded.has(c._idx);
                    return (
                    <tr
                      key={c._idx}
                      className={`transition-opacity hover:bg-paper-deep/50 ${off ? "opacity-35" : ""}`}
                    >
                      <td className="stick px-3 py-2 [--stick-l:0px]">
                        <Checkbox
                          checked={!off}
                          onChange={() => toggleRetenu(c._idx)}
                          aria-label={`Retenir ${c.nom ?? c.siren ?? "cette cession"}`}
                        />
                      </td>
                      <td
                        className={`stick stick-end max-w-[260px] truncate px-3 py-2 [--stick-l:48px] ${off ? "line-through" : ""}`}
                        title={[c.nom, c.objet_social].filter(Boolean).join(" — ") || undefined}
                      >
                        <span className="font-medium">{c.nom ?? ND}</span>
                        {c.naf && <span className="tabular ml-2 text-xs text-ink-mut">{c.naf}</span>}
                        {c.objet_social && (
                          <span className="ml-1.5 cursor-help text-xs text-brass" aria-hidden>
                            ℹ
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {c.ville ?? ND}
                        {c.departement ? ` (${c.departement})` : ""}
                      </td>
                      <td className="tabular px-3 py-2 whitespace-nowrap">{fmtDate(c.date)}</td>
                      <td className="tabular px-3 py-2 text-right whitespace-nowrap">{fmtEuros(c.prix)}</td>
                      <td className="tabular px-3 py-2 text-right whitespace-nowrap">
                        {fmtEuros(c.ca)}
                        {c.ca_annee && <span className="text-xs text-ink-mut"> ({c.ca_annee})</span>}
                      </td>
                      <td className="tabular px-3 py-2 text-right whitespace-nowrap">{fmtEuros(c.ebe)}</td>
                      <td className="tabular px-3 py-2 text-right">
                        {c.pct_ca != null ? fmtPct(c.pct_ca, 0) : ND}
                      </td>
                      <td className="tabular px-3 py-2 text-right">{fmtMult(c.mult_ebe)}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {c.url && (
                          <ExtLink href={c.url} label="BODACC" />
                        )}
                        {c.siren && (
                          <ExtLink
                            href={`https://annuaire-entreprises.data.gouv.fr/entreprise/${c.siren}`}
                            label="Annuaire"
                          />
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableShell>
          </Card>
        )}

        {/* ——— Actions : export + enregistrement dans l'historique ——— */}
        {done && cessions.length > 0 && (
          <Card className="rise-in flex flex-wrap items-start gap-x-10 gap-y-4 p-5">
            <div>
              <Button onClick={exportSelection} busy={busyExport}>
                Exporter la sélection (.xlsx)
              </Button>
              <p className="mt-1.5 text-xs text-ink-mut">
                Fichier Excel formaté : uniquement les {selection.length} cessions retenues.
              </p>
            </div>
            <div className="ml-auto flex items-end gap-3">
              <Field
                label="Libellé de la recherche"
                hint="L'enregistrement alimente l'Historique (ré-export possible)."
              >
                <TextInput
                  value={saveLabel}
                  onChange={(e) => setSaveLabel(e.target.value)}
                  placeholder="ex : Boulangeries IDF, mission X"
                />
              </Field>
              <Button variant="outline" onClick={saveSelection}>
                Enregistrer
              </Button>
            </div>
            {savedId != null && (
              <p className="w-full text-right text-xs text-ok">
                Recherche n° {savedId} enregistrée :{" "}
                <Link href="/historique" className="underline underline-offset-2 hover:text-ink">
                  la consulter dans l&apos;Historique
                </Link>
                .
              </p>
            )}
          </Card>
        )}

        {done && (job.cessions?.length ?? 0) === 0 && (
          <Card className="p-6 text-sm text-ink-mut">
            {job.search && job.search.n_annonces === 0 ? (
              <>
                Aucune annonce BODACC ne correspond à ces mots-clés sur la période. Les cessions
                publiées au BODACC sont des ventes de <em>fonds de commerce</em> : certaines
                activités (services B2B notamment) se vendent surtout par cession de titres, hors
                de ce périmètre. Essayer un terme plus large, retirer le département ou étendre la
                fenêtre.
              </>
            ) : job.search && job.search.n_sans_ca > 0 ? (
              <>
                {job.search.n_annonces} annonce{job.search.n_annonces > 1 ? "s" : ""} trouvée
                {job.search.n_annonces > 1 ? "s" : ""}, mais aucune exploitable :{" "}
                {job.search.n_naf_exclues > 0 &&
                  `${job.search.n_naf_exclues} hors activité (NAF), `}
                {job.search.n_sans_ca} sans CA disponible (comptes confidentiels, art. L232-25).
                Passer « CA requis » à « Non » pour voir ces cessions, ou élargir la fenêtre.
              </>
            ) : (
              <>
                Aucune cession exploitable trouvée sur ces critères : élargir la fenêtre, retirer
                le département, ou viser plus de cessions.
              </>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function ExtLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="label-caps mr-2 text-brass underline-offset-2 hover:underline"
    >
      {label} ↗
    </a>
  );
}
