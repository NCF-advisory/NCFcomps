"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button, ErrorNote, Field, TextInput } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(username.trim(), password);
      router.replace("/comparables");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? "Identifiants invalides."
        : "Connexion impossible — le backend est-il démarré ?");
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen">
      {/* Panneau encre : marque + filigrane registre */}
      <section className="ledger-panel relative hidden w-[44%] flex-col justify-between p-12 text-paper lg:flex">
        <p className="label-caps text-brass-soft">NCF Advisory — outil interne</p>
        <div>
          <h1 className="font-display text-6xl leading-[1.05]" style={{ fontFamily: "var(--font-display)" }}>
            Comparables
            <br />
            <span className="italic text-brass-soft">&amp; Évaluation</span>
          </h1>
          <p className="mt-8 max-w-md text-sm leading-relaxed text-paper/70">
            Bêtas désendettés et multiples de sociétés cotées ; prix de cession des fonds
            de commerce français en % du CA et en multiple d&apos;EBITDA. Sources publiques,
            jugement d&apos;analyste requis.
          </p>
        </div>
        <p className="tabular text-xs text-paper/40">
          β désendetté = β / (1 + (1 − IS) × D/E) — Hamada
        </p>
      </section>

      {/* Formulaire */}
      <section className="flex flex-1 items-center justify-center p-8">
        <form onSubmit={submit} className="rise-in w-full max-w-sm space-y-6">
          <div className="lg:hidden">
            <p className="label-caps text-brass">NCF Advisory</p>
            <h1 className="font-display text-3xl" style={{ fontFamily: "var(--font-display)" }}>
              Comparables &amp; Évaluation
            </h1>
          </div>
          <h2 className="label-caps text-ink-mut">Connexion</h2>
          <Field label="Identifiant">
            <TextInput
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </Field>
          <Field label="Mot de passe">
            <TextInput
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>
          <ErrorNote message={error} />
          <Button type="submit" busy={busy}>
            Entrer
          </Button>
        </form>
      </section>
    </main>
  );
}
