/**
 * Sections masquées temporairement (demande du 2026-07-16) : retirer de cette
 * liste pour réactiver.
 *
 * Seul « Comparables » doit être visible pour l'instant. Le code des sections
 * masquées reste intact ; cette constante est l'unique point de contrôle — la
 * barre de navigation ET la redirection des accès directs par URL s'appuient
 * dessus. Pour réactiver une section, supprimer son href ci-dessous.
 */
export const SECTIONS_MASQUEES: readonly string[] = [
  "/cessions",
  "/secteurs",
  "/historique",
];

/** Vrai si le chemin courant appartient à une section actuellement masquée. */
export function estMasquee(pathname: string): boolean {
  return SECTIONS_MASQUEES.some(
    (href) => pathname === href || pathname.startsWith(href + "/"),
  );
}
