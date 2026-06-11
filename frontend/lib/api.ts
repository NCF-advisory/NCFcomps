/** Client API typé. Toutes les routes passent par le proxy Next (/api -> FastAPI). */

export type CompanyRecord = {
  ticker: string;
  name: string | null;
  country: string | null;
  sector: string | null;
  currency: string | null;
  source: string | null;
  market_cap: number | null;
  total_debt: number | null;
  total_cash: number | null;
  revenue: number | null;
  ebitda: number | null;
  ebit: number | null;
  net_debt: number | null;
  enterprise_value: number | null;
  beta_source: number | null;
  index_used: string | null;
  beta_regression: number | null;
  r2: number | null;
  n_obs: number | null;
  gearing: number | null;
  beta_unlevered: number | null;
  ev_sales: number | null;
  ev_ebitda: number | null;
  ev_ebit: number | null;
  pe_trailing: number | null;
  pe_forward: number | null;
  pb: number | null;
};

export type FieldStats = { median: number; mean: number; min: number; max: number };
export type StatsMap = Record<string, FieldStats>;

/** Synthèse bêta de la sélection : retenu = R² >= min_r2 (sinon affiché mais exclu). */
export type BetaSummary = {
  min_r2: number;
  n_retained: number;
  n_excluded_low_r2: number;
  mean_levered: number | null;
  median_levered: number | null;
  mean_adjusted: number | null;
  mean_unlevered: number | null;
};

export type JobBase = {
  id: string;
  kind: "comparables" | "cessions";
  status: "pending" | "running" | "done" | "error";
  progress: number;
  total: number;
  params: Record<string, unknown>;
  error: string | null;
  created_at: string;
};

export type ComparablesJob = JobBase & {
  records?: CompanyRecord[];
  coverage?: Record<string, "ok" | "partielle" | "vide">;
  stats?: StatsMap;
  beta_summary?: BetaSummary | null;
};

export type Cession = {
  siren: string | null;
  nom: string | null;
  ville: string | null;
  departement: string | null;
  date: string | null;
  categorie: string | null;
  prix: number | null;
  naf: string | null;
  activite: string | null;
  ca: number | null;
  ebe: number | null;
  ebit: number | null;
  ca_annee: number | null;
  pct_ca: number | null;
  mult_ebe: number | null;
  descriptif: string | null;
  url: string | null;
};

export type CessionsSummary = {
  overall: {
    n_total: number;
    n_avec_pct: number;
    n_plausible: number;
    n_pct_outliers: number;
    n_avec_ebe: number;
    n_ebe_outliers: number;
    median_pct_ca: number | null;
    median_mult_ebe: number | null;
    median_prix: number | null;
  };
  by_activite: {
    naf: string;
    activite: string | null;
    n: number;
    median_pct_ca: number | null;
    median_mult_ebe: number | null;
    median_prix: number | null;
    median_ca: number | null;
  }[];
};

/** Entonnoir de recherche : requête élargie exécutée + comptage des exclusions. */
export type CessionsSearch = {
  n_annonces: number;
  n_naf_exclues: number;
  n_sans_ca: number;
  keywords: string[];
  naf_codes: string[];
  naf_labels: string[];
};

export type CessionsJob = JobBase & {
  cessions?: Cession[];
  summary?: CessionsSummary;
  search?: CessionsSearch;
  /** Sélection par défaut (règle d'or : bornes + non-outlier), alignée sur `cessions`. */
  retenu_defaut?: boolean[];
};

export type RunKind = "comparables" | "cessions";

export type RunSummary = {
  id: number;
  created_at: string;
  username: string | null;
  label: string | null;
  params: Record<string, unknown>;
  n_records: number;
  kind: RunKind;
};

export type MetricStat = {
  median: number;
  q1: number;
  q3: number;
  min: number;
  max: number;
  n: number;
};

/** Métriques agrégées d'un secteur : clé = nom du champ CompanyRecord. */
export type SectorAggregate = {
  sector: string;
  n_records: number;
  n_companies: number;
  last_used: string | null;
  metrics: Record<string, MetricStat>;
};

export type SectorRecord = {
  run_id: number;
  created_at: string;
  label: string | null;
  ticker: string | null;
  name: string | null;
  country: string | null;
  beta_unlevered: number | null;
  beta_regression: number | null;
  ev_sales: number | null;
  ev_ebitda: number | null;
  ev_ebit: number | null;
  pe_trailing: number | null;
  pe_forward: number | null;
  pb: number | null;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* corps non JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<{ username: string; name: string | null }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  me: () => request<{ username: string; name: string | null }>("/api/auth/me"),

  // Comparables
  createComparablesJob: (body: {
    tickers: string[];
    tax_rate?: number;
    period?: string;
    frequency?: string;
  }) => request<ComparablesJob>("/api/comparables/jobs", { method: "POST", body: JSON.stringify(body) }),
  comparablesJob: (id: string) => request<ComparablesJob>(`/api/comparables/jobs/${id}`),
  statsFor: (records: CompanyRecord[]) =>
    request<{ n: number; stats: StatsMap; beta_summary: BetaSummary | null }>(
      "/api/comparables/stats",
      { method: "POST", body: JSON.stringify({ records }) },
    ),
  resolveNames: (names: string[]) =>
    request<{ results: { query: string; match: { symbol: string; name: string; exchange: string } | null }[] }>(
      "/api/comparables/resolve",
      { method: "POST", body: JSON.stringify({ names }) },
    ),

  // Cessions
  createCessionsJob: (body: {
    departement?: string;
    contains?: string;
    since?: string;
    limit?: number;
    require_ca?: boolean;
  }) => request<CessionsJob>("/api/cessions/jobs", { method: "POST", body: JSON.stringify(body) }),
  cessionsJob: (id: string) => request<CessionsJob>(`/api/cessions/jobs/${id}`),
  cessionsStats: (cessions: Cession[]) =>
    request<{ n: number; summary: CessionsSummary }>("/api/cessions/stats", {
      method: "POST",
      body: JSON.stringify({ cessions }),
    }),
  saveCessionsRun: (cessions: Cession[], label?: string, params?: Record<string, unknown>) =>
    request<{ id: number }>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ cessions, label, params }),
    }),

  // Runs
  listRuns: () => request<{ runs: RunSummary[] }>("/api/runs"),
  saveRun: (records: CompanyRecord[], label?: string, params?: Record<string, unknown>) =>
    request<{ id: number }>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ records, label, params }),
    }),
  getRun: (id: number) =>
    request<{ id: number; kind: RunKind; records?: CompanyRecord[]; cessions?: Cession[] }>(
      `/api/runs/${id}`,
    ),
  deleteRun: (id: number) => request<void>(`/api/runs/${id}`, { method: "DELETE" }),

  // Base sectorielle (bêtas + multiples agrégés depuis l'historique enregistré)
  listSectors: () => request<{ sectors: SectorAggregate[] }>("/api/sectors"),
  sectorDetail: (sector: string) =>
    request<{ sector: string; records: SectorRecord[] }>(
      `/api/sectors/${encodeURIComponent(sector)}`,
    ),
};

/** Télécharge un .xlsx produit par l'API (POST records ou GET run). */
export async function downloadExcel(records: CompanyRecord[], filename = "comparables.xlsx") {
  const res = await fetch("/api/comparables/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ records }),
  });
  if (!res.ok) throw new ApiError(res.status, "Export impossible.");
  triggerDownload(await res.blob(), filename);
}

export async function downloadRunExcel(runId: number, kind: RunKind = "comparables") {
  const res = await fetch(`/api/runs/${runId}/export`);
  if (!res.ok) throw new ApiError(res.status, "Export impossible.");
  const prefix = kind === "cessions" ? "cessions_fr_run" : "comparables_run";
  triggerDownload(await res.blob(), `${prefix}_${runId}.xlsx`);
}

/** Télécharge le .xlsx des cessions sélectionnées. */
export async function downloadCessionsExcel(cessions: Cession[], filename = "cessions_fr.xlsx") {
  const res = await fetch("/api/cessions/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cessions }),
  });
  if (!res.ok) throw new ApiError(res.status, "Export impossible.");
  triggerDownload(await res.blob(), filename);
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Boucle d'attente d'un job (poll ~0,8 s) avec rappel de progression. */
export async function pollJob<T extends JobBase>(
  fetchJob: () => Promise<T>,
  onTick: (job: T) => void,
  intervalMs = 800,
): Promise<T> {
  for (;;) {
    const job = await fetchJob();
    onTick(job);
    if (job.status === "done" || job.status === "error") return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
