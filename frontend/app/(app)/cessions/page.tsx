"use client";

/** Module II — Cessions de fonds de commerce (France) : % du CA et multiple d'EBITDA.
 *
 * Métrique de marge = EBE des comptes sociaux, utilisé comme proxy d'EBITDA (champ
 * interne `ebe`/`mult_ebe`, affiché « EBITDA »). Sources publiques gratuites : BODACC
 * (prix), ratios INPI/BCE (CA, EBE), Recherche d'entreprises (NAF). Couverture
 * partielle : comptes confidentiels (~45 %) exclus.
 */

import { useState } from "react";

import { api, type CessionsJob, pollJob } from "@/lib/api";
import { fmtDate, fmtEuros, fmtMult, fmtPct, ND } from "@/lib/format";
import {
  Button,
  Card,
  Disclosure,
  ErrorNote,
  Field,
  JobProgress,
  PageTitle,
  Select,
  TextInput,
  Th,
} from "@/components/ui";

export default function CessionsPage() {
  const [contains, setContains] = useState("");
  const [departement, setDepartement] = useState("");
  const [years, setYears] = useState("10");
  const [limit, setLimit] = useState("50");

  const [job, setJob] = useState<CessionsJob | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function launch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setJob(null);
    setRunning(true);
    try {
      const since = new Date();
      since.setFullYear(since.getFullYear() - Number(years));
      const created = await api.createCessionsJob({
        contains: contains.trim() || undefined,
        departement: departement.trim() || undefined,
        since: since.toISOString().slice(0, 10),
        limit: Number(limit),
      });
      setJob(created);
      const finished = await pollJob(() => api.cessionsJob(created.id), setJob);
      if (finished.status === "error") setError(finished.error ?? "Échec de la recherche.");
    } catch {
      setError("Échec du lancement — le backend est-il démarré ?");
    } finally {
      setRunning(false);
    }
  }

  const done = job?.status === "done";
  const overall = job?.summary?.overall;

  return (
    <div>
      <PageTitle
        kicker="Module II"
        title="Cessions de fonds de commerce — France"
        lede="Rechercher les cessions publiées au BODACC par activité ou département : l'outil
        rapproche chaque prix du CA et de l'EBITDA de la société cédante, puis en tire un barème
        par activité."
      />
      <Disclosure summary="Méthode & sources">
        <p>
          <strong className="text-ink">Sources publiques gratuites</strong> : BODACC (prix de
          cession), ratios INPI/Banque de France et comptes déposés à l&apos;INPI (CA, EBE) —
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
          Ordre de grandeur indicatif — chaque ligne est vérifiable (liens BODACC / Annuaire).
        </p>
      </Disclosure>

      {/* ——— Formulaire ——— */}
      <Card className="p-6">
        <form onSubmit={launch} className="grid grid-cols-2 items-end gap-4 md:grid-cols-5">
          <Field label="Activité (texte libre)" hint="ex : boulangerie, pharmacie, restaurant">
            <TextInput value={contains} onChange={(e) => setContains(e.target.value)} />
          </Field>
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
            </Select>
          </Field>
          <Field label="Nombre de cessions" hint="objectif de lignes exploitables (CA connu)">
            <Select value={limit} onChange={(e) => setLimit(e.target.value)}>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </Select>
          </Field>
          <Button type="submit" busy={running}>
            Rechercher
          </Button>
        </form>
      </Card>

      <div className="mt-6 space-y-6">
        <ErrorNote message={error} />

        {job && !done && job.status !== "error" && (
          <Card className="p-6">
            <JobProgress
              progress={job.progress}
              total={job.total}
              label="Recherche BODACC + enrichissement INPI (peut prendre quelques minutes)"
            />
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
        {done && (job.summary?.by_activite.length ?? 0) > 0 && (
          <Card className="rise-in overflow-x-auto">
            <h2 className="label-caps border-b border-hairline px-4 py-3 text-ink-mut">
              Barème par activité (NAF) — médianes robustes
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink bg-paper-deep text-left">
                  <Th left tip="Code d'activité principale (nomenclature NAF)">NAF</Th>
                  <Th tip="Nombre de cessions retenues dans l'activité">n</Th>
                  <Th tip="Médiane des prix de cession rapportés au CA">% du CA</Th>
                  <Th tip="Médiane des prix rapportés à l'EBITDA (EBE des comptes sociaux)">× EBITDA</Th>
                  <Th>Prix médian</Th>
                  <Th>CA médian</Th>
                </tr>
              </thead>
              <tbody>
                {job.summary!.by_activite.map((g) => (
                  <tr key={g.naf} className="border-b border-hairline hover:bg-paper-deep/50">
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
          </Card>
        )}

        {/* ——— Détail des cessions ——— */}
        {done && (job.cessions?.length ?? 0) > 0 && (
          <Card className="rise-in overflow-x-auto">
            <h2 className="label-caps border-b border-hairline px-4 py-3 text-ink-mut">
              Détail des cessions ({job.cessions!.length})
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink bg-paper-deep text-left">
                  <Th left>Entreprise</Th>
                  <Th left>Lieu</Th>
                  <Th left>Date</Th>
                  <Th tip="Prix de cession publié au BODACC">Prix</Th>
                  <Th tip="Chiffre d'affaires du dernier exercice clos avant la cession">
                    CA (exercice)
                  </Th>
                  <Th tip="EBE des comptes sociaux — proxy d'EBITDA">EBITDA</Th>
                  <Th tip="Prix de cession / CA">% CA</Th>
                  <Th tip="Prix de cession / EBITDA">× EBITDA</Th>
                  <Th left tip="Sources officielles pour contrôler la ligne">Vérifier</Th>
                </tr>
              </thead>
              <tbody>
                {job.cessions!.map((c, i) => (
                  <tr key={`${c.siren}-${i}`} className="border-b border-hairline hover:bg-paper-deep/50">
                    <td className="px-3 py-2">
                      <span className="font-medium">{c.nom ?? ND}</span>
                      {c.naf && <span className="tabular ml-2 text-xs text-ink-mut">{c.naf}</span>}
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
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {done && (job.cessions?.length ?? 0) === 0 && (
          <Card className="p-6 text-sm text-ink-mut">
            Aucune cession exploitable trouvée sur ces critères — élargir la fenêtre, retirer le
            département, ou viser plus de cessions.
          </Card>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="p-5">
      <p className="label-caps text-ink-mut">{label}</p>
      <p
        className="tabular mt-2 font-display text-4xl text-ink"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {value}
      </p>
      <p className="mt-2 text-xs text-ink-mut">{note}</p>
    </Card>
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
