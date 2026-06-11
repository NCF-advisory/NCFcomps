"use client";

/** Toasts de confirmation (bas-droite, auto-effacés). Bus module-level :
 * `toast("Export téléchargé")` depuis n'importe quel composant client ;
 * un seul <Toaster /> monté dans le layout applicatif. */

import { useCallback, useEffect, useRef, useState } from "react";

type Tone = "ok" | "alert";
type ToastMsg = { id: number; text: string; tone: Tone; leaving?: boolean };

let pushImpl: ((text: string, tone: Tone) => void) | null = null;
let nextId = 1;

export function toast(text: string, tone: Tone = "ok") {
  pushImpl?.(text, tone);
}

const SHOW_MS = 4000;
const LEAVE_MS = 250;

export function Toaster() {
  const [items, setItems] = useState<ToastMsg[]>([]);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), LEAVE_MS);
  }, []);

  useEffect(() => {
    const timeouts = timers.current;
    pushImpl = (text, tone) => {
      const id = nextId++;
      setItems((prev) => [...prev.slice(-3), { id, text, tone }]);
      timeouts.set(id, setTimeout(() => dismiss(id), SHOW_MS));
    };
    return () => {
      pushImpl = null;
      timeouts.forEach(clearTimeout);
    };
  }, [dismiss]);

  if (items.length === 0) return null;
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {items.map((t) => (
        <button
          key={t.id}
          onClick={() => dismiss(t.id)}
          className={`toast-item cursor-pointer ${t.tone === "alert" ? "tone-alert" : ""} ${
            t.leaving ? "leaving" : ""
          }`}
        >
          {t.text}
        </button>
      ))}
    </div>
  );
}
