"use client";

/** Mécanique des tableaux financiers : coque de défilement (ombres + classe
 * `is-x` quand on a quitté la butée gauche, pour l'ombre du rail d'identité)
 * et tri par colonne. Les styles structurants (.table-fin, .stick…) vivent
 * dans globals.css. */

import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

/** Conteneur de tableau : unique contexte de scroll (sticky top + left). */
export function TableShell({
  children,
  capped = true,
  className = "",
}: {
  children: ReactNode;
  /** Limite la hauteur (l'en-tête colle alors au défilement vertical). */
  capped?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [scrolledX, setScrolledX] = useState(false);
  const [moreRight, setMoreRight] = useState(false);

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setScrolledX(el.scrollLeft > 2);
    setMoreRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
  }, []);

  useEffect(() => {
    update();
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    return () => ro.disconnect();
  }, [update]);

  return (
    <div className={`relative ${className}`}>
      <div
        ref={ref}
        onScroll={update}
        className={`table-shell ${capped ? "table-shell-capped" : ""} ${scrolledX ? "is-x" : ""}`}
      >
        {children}
      </div>
      <div aria-hidden className={`scroll-shade shade-r ${moreRight ? "on" : ""}`} />
    </div>
  );
}

export type SortDir = 1 | -1;
export type SortState = { key: string; dir: SortDir } | null;

/** Tri par colonne : 1er clic = ordre « naturel » (desc pour les nombres,
 * asc pour le texte), 2e clic = inverse, 3e = retour à l'ordre d'origine.
 * Les valeurs absentes restent toujours en bas. */
export function useSort<T extends Record<string, unknown>>(rows: T[]) {
  const [sort, setSort] = useState<SortState>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const { key, dir } = sort;
    return [...rows].sort((a, b) => {
      const va = a[key];
      const vb = b[key];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "fr", { sensitivity: "base" }) * dir;
    });
  }, [rows, sort]);

  const toggle = useCallback(
    (key: string) => {
      setSort((prev) => {
        if (prev?.key !== key) {
          const sample = rows.find((r) => r[key] != null)?.[key];
          return { key, dir: typeof sample === "number" ? -1 : 1 };
        }
        const sample = rows.find((r) => r[key] != null)?.[key];
        const first: SortDir = typeof sample === "number" ? -1 : 1;
        return prev.dir === first ? { key, dir: (-first) as SortDir } : null;
      });
    },
    [rows],
  );

  const dirFor = useCallback(
    (key: string): SortDir | null => (sort?.key === key ? sort.dir : null),
    [sort],
  );

  return { sorted, toggle, dirFor };
}
