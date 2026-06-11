"use client";

/** Primitives UI du design system « registre » : boutons, cartes, champs, badges. */

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
  const base =
    "inline-flex items-center gap-2 px-4 py-2 label-caps transition-colors duration-150 " +
    "disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer select-none " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-brass)]";
  const variants = {
    primary: "bg-ink text-paper hover:bg-ink-soft",
    outline: "border border-brass text-ink hover:bg-brass/10",
    ghost: "text-ink-mut hover:text-ink",
    danger: "border border-alert/40 text-alert hover:bg-alert/10",
  } as const;
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`${base} ${variants[variant]}`}
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
  return (
    <div className={`border border-hairline bg-card shadow-[0_1px_2px_rgba(17,36,29,0.05)] ${className}`}>
      {children}
    </div>
  );
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

const inputClass =
  "w-full border border-hairline bg-card px-3 py-2 text-sm text-ink outline-none " +
  "transition-colors focus:border-brass placeholder:text-ink-mut/60";

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={inputClass} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputClass} tabular min-h-28 resize-y`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputClass} cursor-pointer`} />;
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
    <span className={`inline-block border px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function PageTitle({ kicker, title, lede }: { kicker: string; title: string; lede?: string }) {
  return (
    <header className="mb-10">
      <p className="label-caps text-brass">{kicker}</p>
      <h1 className="rule-brass mt-1 font-display text-4xl text-ink" style={{ fontFamily: "var(--font-display)" }}>
        {title}
      </h1>
      {lede && <p className="mt-6 max-w-2xl text-sm leading-relaxed text-ink-mut">{lede}</p>}
    </header>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="border border-alert/30 bg-alert/8 px-3 py-2 text-sm text-alert" role="alert">
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
      <summary className="label-caps cursor-pointer list-none text-ink-mut transition-colors hover:text-ink">
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
