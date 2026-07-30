import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const URL_VALIDATION_BASE = "https://runtime-config.invalid/";
const PINNED_HUGGING_FACE_REVISION = /^[0-9a-f]{40,64}$/i;

export function isSafePrecomputedAudioManifestUrl(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return false;
  }

  let parsed;
  try {
    parsed = new URL(trimmed, URL_VALIDATION_BASE);
  } catch {
    return false;
  }
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return false;
  }
  if (parsed.hostname.toLowerCase() !== "huggingface.co") {
    return true;
  }

  const pathParts = parsed.pathname.split("/").filter(Boolean);
  const resolveIndex = pathParts.indexOf("resolve");
  if (resolveIndex < 0 || resolveIndex + 1 >= pathParts.length) {
    return false;
  }
  try {
    return PINNED_HUGGING_FACE_REVISION.test(
      decodeURIComponent(pathParts[resolveIndex + 1]),
    );
  } catch {
    return false;
  }
}

export async function configurePrecomputedAudioRuntime({
  runtimeConfigPath,
  manifestUrl,
}) {
  let runtimeConfig = {};
  try {
    const payload = JSON.parse(await readFile(runtimeConfigPath, "utf8"));
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error("runtime config must contain a JSON object");
    }
    runtimeConfig = payload;
  } catch (error) {
    if (error?.code !== "ENOENT") {
      throw error;
    }
  }

  const suppliedManifestUrl = String(manifestUrl ?? "").trim();
  const existingManifestUrl =
    typeof runtimeConfig.precomputedAudio?.manifestUrl === "string"
      ? runtimeConfig.precomputedAudio.manifestUrl.trim()
      : "";
  const selectedManifestUrl = suppliedManifestUrl || existingManifestUrl;

  if (!selectedManifestUrl) {
    return false;
  }
  if (!isSafePrecomputedAudioManifestUrl(selectedManifestUrl)) {
    throw new Error(
      "precomputed audio manifest URL is invalid or uses a mutable Hugging Face revision",
    );
  }
  if (!suppliedManifestUrl) {
    return false;
  }

  const existingPrecomputedAudio =
    runtimeConfig.precomputedAudio &&
    typeof runtimeConfig.precomputedAudio === "object" &&
    !Array.isArray(runtimeConfig.precomputedAudio)
      ? runtimeConfig.precomputedAudio
      : {};
  runtimeConfig.precomputedAudio = {
    ...existingPrecomputedAudio,
    manifestUrl: selectedManifestUrl,
  };
  await writeFile(runtimeConfigPath, `${JSON.stringify(runtimeConfig, null, 2)}\n`);
  return true;
}

async function main() {
  const runtimeConfigPath = resolve(process.argv[2] || "public/runtime-config.json");
  await configurePrecomputedAudioRuntime({
    runtimeConfigPath,
    manifestUrl: process.env.ABBY_PAGES_PRECOMPUTED_AUDIO_MANIFEST_URL,
  });
}

const entryPoint = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : "";
if (import.meta.url === entryPoint) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
