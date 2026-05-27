interface PrecomputedAudioManifest {
  responses?: PrecomputedAudioManifestEntry[];
}

interface PrecomputedAudioManifestEntry {
  id: string;
  text?: string;
  originalTexts?: string[];
  routes?: string[];
  status?: string;
  audioUrl?: string;
  mp3Url?: string;
  preferredAudioUrl?: string;
}

interface PreparedPrecomputedAudioEntry extends PrecomputedAudioManifestEntry {
  resolvedAudioUrl: string;
  normalizedText: string;
  normalizedOriginalTexts: string[];
  normalizedRoutes: Set<string>;
}

export interface PrecomputedAudioReplyMatch {
  id: string;
  audioUrl: string;
  text: string;
  matchedText: string;
  route?: string;
}

const PRECOMPUTED_AUDIO_MANIFEST_URL = "/assets/audio/precomputed/211-dag-indextts/manifest.json";

let manifestPromise: Promise<PreparedPrecomputedAudioEntry[] | undefined> | undefined;

export async function findPrecomputedAudioReply(input: {
  candidateTexts: string[];
  routeHints?: string[];
}): Promise<PrecomputedAudioReplyMatch | undefined> {
  const manifest = await loadPrecomputedAudioManifest();
  if (!manifest?.length) {
    return undefined;
  }

  const normalizedCandidates = dedupeStrings(input.candidateTexts.map(normalizePrecomputedAudioText).filter(Boolean));
  if (!normalizedCandidates.length) {
    return undefined;
  }
  const normalizedRouteHints = new Set((input.routeHints || []).map(normalizeRouteHint).filter(Boolean));

  let bestMatch:
    | {
        entry: PreparedPrecomputedAudioEntry;
        matchedText: string;
        score: number;
      }
    | undefined;
  for (const entry of manifest) {
    const matchedOriginalText = entry.normalizedOriginalTexts.find((candidate) => normalizedCandidates.includes(candidate));
    const matchedText = normalizedCandidates.find((candidate) => candidate === entry.normalizedText) || matchedOriginalText;
    if (!matchedText) {
      continue;
    }
    const score =
      (matchedText === entry.normalizedText ? 2 : 1) +
      (hasMatchingRoute(entry.normalizedRoutes, normalizedRouteHints) ? 0.25 : 0);
    if (!bestMatch || score > bestMatch.score) {
      bestMatch = {
        entry,
        matchedText,
        score,
      };
    }
  }

  if (!bestMatch) {
    return undefined;
  }
  return {
    id: bestMatch.entry.id,
    audioUrl: bestMatch.entry.resolvedAudioUrl,
    text: bestMatch.entry.text?.trim() || bestMatch.entry.originalTexts?.[0]?.trim() || "",
    matchedText: bestMatch.matchedText,
    route: bestMatch.entry.routes?.[0],
  };
}

async function loadPrecomputedAudioManifest(): Promise<PreparedPrecomputedAudioEntry[] | undefined> {
  if (!manifestPromise) {
    manifestPromise = fetch(PRECOMPUTED_AUDIO_MANIFEST_URL, { cache: "force-cache" })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Precomputed audio manifest unavailable (${response.status})`);
        }
        const manifest = (await response.json()) as PrecomputedAudioManifest;
        return prepareManifestEntries(manifest.responses || []);
      })
      .catch((error) => {
        console.warn("Precomputed audio manifest unavailable; continuing with generated speech.", error);
        return undefined;
      });
  }
  return manifestPromise;
}

function prepareManifestEntries(entries: PrecomputedAudioManifestEntry[]): PreparedPrecomputedAudioEntry[] {
  return entries
    .map((entry) => {
      const resolvedAudioUrl = resolveAudioUrl(entry);
      if (!resolvedAudioUrl) {
        return undefined;
      }
      return {
        ...entry,
        resolvedAudioUrl,
        normalizedText: normalizePrecomputedAudioText(entry.text || ""),
        normalizedOriginalTexts: dedupeStrings((entry.originalTexts || []).map(normalizePrecomputedAudioText).filter(Boolean)),
        normalizedRoutes: new Set((entry.routes || []).map(normalizeRouteHint).filter(Boolean)),
      };
    })
    .filter((entry): entry is PreparedPrecomputedAudioEntry => Boolean(entry));
}

function resolveAudioUrl(entry: PrecomputedAudioManifestEntry): string | undefined {
  const candidate = entry.preferredAudioUrl || entry.mp3Url || entry.audioUrl;
  if (!candidate?.trim()) {
    return undefined;
  }
  try {
    return new URL(candidate, document.baseURI).toString();
  } catch {
    return candidate;
  }
}

function hasMatchingRoute(entryRoutes: Set<string>, routeHints: Set<string>): boolean {
  if (!entryRoutes.size || !routeHints.size) {
    return false;
  }
  for (const routeHint of routeHints) {
    if (entryRoutes.has(routeHint)) {
      return true;
    }
  }
  return false;
}

function normalizePrecomputedAudioText(value: string): string {
  return value
    .toLowerCase()
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\[[0-9]+\]/g, " ")
    .replace(/\b(?:sources?|evidence|citations?|next steps?)\s*:[\s\S]*$/i, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeRouteHint(value: string): string {
  return value.trim().toLowerCase();
}

function dedupeStrings(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}