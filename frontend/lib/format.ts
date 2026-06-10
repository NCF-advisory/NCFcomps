/** Formats d'affichage français (montants en M, %, multiples, bêtas). */

const NUM = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const DEC2 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const DEC1 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const ND = "n.d.";

export function fmtMillions(v: number | null | undefined): string {
  if (v == null) return ND;
  return NUM.format(v / 1_000_000);
}

export function fmtEuros(v: number | null | undefined): string {
  if (v == null) return ND;
  return `${NUM.format(v)} €`;
}

export function fmtBeta(v: number | null | undefined): string {
  return v == null ? ND : DEC2.format(v);
}

export function fmtPct(v: number | null | undefined, digits: 0 | 1 = 1): string {
  if (v == null) return ND;
  return `${(digits === 1 ? DEC1 : NUM).format(v * 100)} %`;
}

export function fmtMult(v: number | null | undefined): string {
  return v == null ? ND : `${DEC1.format(v)}x`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return ND;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR");
}
