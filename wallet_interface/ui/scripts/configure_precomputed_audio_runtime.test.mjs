import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  configurePrecomputedAudioRuntime,
  isSafePrecomputedAudioManifestUrl,
} from "./configure_precomputed_audio_runtime.mjs";

const pinnedRevision = "a".repeat(40);
const pinnedManifestUrl =
  `https://huggingface.co/datasets/Publicus/211-abby-tts/resolve/${pinnedRevision}` +
  "/data/abby_voice_v2/release-1/metadata/runtime-precomputed-audio-manifest.json";

test("writes an explicitly selected immutable manifest without discarding runtime config", async () => {
  const root = await mkdtemp(join(tmpdir(), "abby-runtime-config-"));
  const runtimeConfigPath = join(root, "runtime-config.json");
  await writeFile(
    runtimeConfigPath,
    `${JSON.stringify({ walletApi: { apiBaseUrl: "same-origin" } })}\n`,
  );

  const changed = await configurePrecomputedAudioRuntime({
    runtimeConfigPath,
    manifestUrl: pinnedManifestUrl,
  });
  const payload = JSON.parse(await readFile(runtimeConfigPath, "utf8"));

  assert.equal(changed, true);
  assert.equal(payload.walletApi.apiBaseUrl, "same-origin");
  assert.equal(payload.precomputedAudio.manifestUrl, pinnedManifestUrl);
});

test("rejects mutable Hugging Face revisions without changing the config", async () => {
  const root = await mkdtemp(join(tmpdir(), "abby-runtime-config-"));
  const runtimeConfigPath = join(root, "runtime-config.json");
  const original = `${JSON.stringify({ walletApi: { apiBaseUrl: "same-origin" } })}\n`;
  await writeFile(runtimeConfigPath, original);

  await assert.rejects(
    configurePrecomputedAudioRuntime({
      runtimeConfigPath,
      manifestUrl:
        "https://huggingface.co/datasets/Publicus/211-abby-tts/resolve/main/manifest.json",
    }),
    /mutable Hugging Face revision/,
  );
  assert.equal(await readFile(runtimeConfigPath, "utf8"), original);
  assert.equal(
    isSafePrecomputedAudioManifestUrl(
      "https://huggingface.co/datasets/Publicus/211-abby-tts/resolve/latest/manifest.json",
    ),
    false,
  );
});

test("rejects a committed mutable fallback when no Pages override is supplied", async () => {
  const root = await mkdtemp(join(tmpdir(), "abby-runtime-config-"));
  const runtimeConfigPath = join(root, "runtime-config.json");
  await writeFile(
    runtimeConfigPath,
    `${JSON.stringify({
      precomputedAudio: {
        manifestUrl:
          "https://huggingface.co/datasets/Publicus/211-abby-tts/resolve/master/manifest.json",
      },
    })}\n`,
  );

  await assert.rejects(
    configurePrecomputedAudioRuntime({ runtimeConfigPath, manifestUrl: "" }),
    /mutable Hugging Face revision/,
  );
});
