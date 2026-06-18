/** Feature-flag system — the web mirror of `api/app/features.py`.
 *
 * ONE declaration drives both stacks: the backend reads `APP_MODULES`, the web
 * reads `NEXT_PUBLIC_APP_MODULES` (same comma list). Keep this registry in sync
 * with the Python one — same keys, same `requires`.
 *
 * `NEXT_PUBLIC_*` is build-time inlined, so the enabled set is fixed at build.
 * Module UIs are loaded via `next/dynamic` guarded by `isEnabled`, so a disabled
 * feature's code sits in its own lazy chunk and is never fetched — an app that
 * doesn't use it doesn't pay for it.
 */
export type FeatureKey = "chat" | "cms" | "marketplace";

export interface FeatureDef {
  label: string;
  core?: boolean;
  requires?: FeatureKey[];
}

export const FEATURES: Record<FeatureKey, FeatureDef> = {
  chat: { label: "Asistente / chat", core: true },
  cms: { label: "Manejador de contenido" },
  marketplace: { label: "Marketplace / tienda" },
};

export const CORE_FEATURES: FeatureKey[] = (Object.keys(FEATURES) as FeatureKey[]).filter(
  (k) => FEATURES[k].core,
);

/** Resolve an APP_MODULES declaration into the enabled set: core always on,
 * declared features pull in their `requires` transitively, unknown keys dropped
 * with a warning (never throws — a typo degrades to "feature off"). */
export function resolveFeatures(raw: string | null | undefined): Set<FeatureKey> {
  const enabled = new Set<FeatureKey>(CORE_FEATURES);
  const pending = (raw ?? "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  const seen = new Set<string>();
  while (pending.length) {
    const key = pending.pop() as string;
    if (seen.has(key)) continue;
    seen.add(key);
    if (!(key in FEATURES)) {
      console.warn(`NEXT_PUBLIC_APP_MODULES names unknown feature "${key}" — ignored`);
      continue;
    }
    const k = key as FeatureKey;
    enabled.add(k);
    for (const req of FEATURES[k].requires ?? []) pending.push(req);
  }
  return enabled;
}

/** Enabled features for this build (NEXT_PUBLIC_APP_MODULES, inlined). */
export const ENABLED_FEATURES: Set<FeatureKey> = resolveFeatures(
  process.env.NEXT_PUBLIC_APP_MODULES,
);

export function isEnabled(key: FeatureKey): boolean {
  return ENABLED_FEATURES.has(key);
}
