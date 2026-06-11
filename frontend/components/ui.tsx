"use client";

/** Primitives UI de la charte « Institutionnel clair v2 » : boutons, cartes,
 * champs, badges. Les styles structurants (btn-*, field-input, card-surface,
 * section-*) vivent dans globals.css, copiés depuis CHARTE-GRAPHIQUE.md. */

import { type ReactNode } from "react";

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  busy,
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "outline" | "ghost" | "danger";
  disabled?: boolean;
  busy?: boolean;
}) {
  const variants = {
    primary: "btn-primary",
    outline: "btn-outline",
    ghost: "btn-ghost",
    danger: "btn-danger",
  } as const;
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`btn-base ${variants[variant]} disabled:cursor-not-allowed disabled:opacity-45`}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block size-3.5 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
    />
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card-surface ${className}`}>{children}</div>;
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="label-caps text-ink-mut">{label}</span>
      <div className="mt-1.5">{children}</div>
      {hint && <p className="mt-1 text-xs text-ink-mut">{hint}</p>}
    </label>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className="field-input" />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className="field-input tabular min-h-28 resize-y" />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className="field-input cursor-pointer" />;
}

export function Badge({
  tone,
  children,
}: {
  tone: "ok" | "warn" | "alert" | "neutral";
  children: ReactNode;
}) {
  const tones = {
    ok: "text-ok border-ok/30 bg-ok/8",
    warn: "text-warn border-warn/30 bg-warn/8",
    alert: "text-alert border-alert/30 bg-alert/8",
    neutral: "text-ink-mut border-hairline bg-paper",
  } as const;
  return (
    <span
      className={`inline-block rounded-[4px] border px-1.5 py-0.5 text-[0.65rem] font-bold tracking-[0.08em] uppercase ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function PageTitle({ kicker, title, lede }: { kicker: string; title: string; lede?: string }) {
  return (
    <header className="mb-10">
      <p className="section-eyebrow mb-3">{kicker}</p>
      <h1 className="section-title">{title}</h1>
      {lede && <p className="section-sub">{lede}</p>}
    </header>
  );
}

/** Carte statistique : grand chiffre + libellé + note explicative. */
export function StatCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="p-5">
      <p className="label-caps text-ink-mut">{label}</p>
      <p className="tabular mt-2 text-4xl font-extrabold tracking-[-0.028em] text-ink-strong">
        {value}
      </p>
      <p className="mt-2 text-xs text-ink-mut">{note}</p>
    </Card>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      className="rounded-[8px] border border-alert/30 bg-alert/8 px-3 py-2 text-sm text-alert"
      role="alert"
    >
      {message}
    </p>
  );
}

/** En-tête de colonne de tableau ; `tip` ajoute une infobulle (soulignement pointillé). */
export function Th({
  children,
  left,
  tip,
  className = "",
}: {
  children: ReactNode;
  left?: boolean;
  tip?: string;
  className?: string;
}) {
  return (
    <th
      title={tip}
      className={`label-caps px-3 py-2.5 whitespace-nowrap text-ink-mut ${left ? "text-left" : "text-right"} ${
        tip ? "cursor-help underline decoration-ink-mut/40 decoration-dotted underline-offset-4" : ""
      } ${className}`}
    >
      {children}
    </th>
  );
}

/** Cellule numérique alignée à droite (chiffres tabulaires). */
export function Td({
  children,
  dense,
  className = "",
}: {
  children: ReactNode;
  dense?: boolean;
  className?: string;
}) {
  return (
    <td className={`tabular px-3 ${dense ? "py-1.5" : "py-2"} text-right whitespace-nowrap ${className}`}>
      {children}
    </td>
  );
}

/** Bloc repliable « Méthode & sources » : garde les ledes courtes, le détail à un clic. */
export function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="group -mt-6 mb-8 max-w-2xl">
      <summary className="label-caps cursor-pointer list-none text-ink-mut transition-colors hover:text-ink-strong">
        <span className="mr-1.5 inline-block text-brass transition-transform group-open:rotate-90">▸</span>
        {summary}
      </summary>
      <div className="mt-3 space-y-2 border-l-2 border-brass/40 pl-4 text-sm leading-relaxed text-ink-mut">
        {children}
      </div>
    </details>
  );
}

/** Barre de progression d'un job (déterminée si total > 0). */
export function JobProgress({
  progress,
  total,
  label,
}: {
  progress: number;
  total: number;
  label: string;
}) {
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
  return (
    <div className="rise-in">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="label-caps text-ink-mut">{label}</span>
        <span className="tabular text-sm text-ink">
          {total > 0 ? `${progress} / ${total}` : "…"}
        </span>
      </div>
      <div className="progress-track">
        <div
          className={`progress-fill ${total === 0 ? "progress-indeterminate" : ""}`}
          style={total > 0 ? { width: `${pct}%` } : undefined}
        />
      </div>
    </div>
  );
}
