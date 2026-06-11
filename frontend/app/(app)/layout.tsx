"use client";

/** Shell authentifié : sidebar « registre » + garde d'authentification (/api/auth/me). */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";

const NAV = [
  { href: "/comparables", label: "Comparables boursiers", num: "I" },
  { href: "/cessions", label: "Cessions FR", num: "II" },
  { href: "/secteurs", label: "Base sectorielle", num: "III" },
  { href: "/historique", label: "Historique", num: "IV" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<{ username: string; name: string | null } | null>(null);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
      });
  }, [router]);

  async function logout() {
    await api.logout().catch(() => undefined);
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="band-panel sticky top-0 flex h-screen w-60 shrink-0 flex-col overflow-y-auto p-6">
        <Link href="/comparables" className="block">
          <span className="text-2xl font-extrabold tracking-[-0.02em] text-white">NCF</span>
          <span className="mt-1 block text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-brass-soft">
            Comparables &amp; Évaluation
          </span>
        </Link>

        <nav className="mt-12 flex flex-col gap-1">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-baseline gap-3 rounded-[8px] border-l-2 px-3 py-2.5 text-sm transition-colors ${
                  active
                    ? "border-brass-soft bg-white/8 font-medium text-white"
                    : "border-transparent text-paper/70 hover:text-white"
                }`}
              >
                <span className="label-caps text-[0.62rem] text-brass-soft">{item.num}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto space-y-3 border-t border-white/15 pt-4">
          {user && (
            <p className="text-xs text-paper/70">
              Session : <span className="text-white">{user.name ?? user.username}</span>
            </p>
          )}
          <button
            onClick={logout}
            className="label-caps cursor-pointer text-paper/60 transition-colors hover:text-brass-soft"
          >
            Déconnexion
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-12 py-10">{children}</main>
    </div>
  );
}
