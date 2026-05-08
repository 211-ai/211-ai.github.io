import { expect, test, type Locator, type Page } from "@playwright/test";

test("assistant opens, searches food pantry evidence, navigates, and gates saving", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "Mobile Safari", "Full GraphRAG planner smoke is covered in Desktop Chrome.");
  test.setTimeout(90000);
  await enterSignedInApp(page);
  await installTiny211Corpus(page);

  await openTextAssistant(page);
  const assistant = visibleAssistant(page);
  await expect(assistant).toBeVisible();
  await expect(assistant.getByText(/I will ask before changing wallet data/i)).toBeVisible();

  await sendAssistantMessage(assistant, "open services");
  await expect(page.getByRole("heading", { name: /Find support/i })).toBeVisible({ timeout: 15000 });
  await expect(assistant.getByText(/Opened Services/i).first()).toBeVisible({ timeout: 15000 });

  await sendAssistantMessage(assistant, "find food pantry evidence near Portland");
  await expect(assistant.getByText(/Found \d+ service records/i).first()).toBeVisible({ timeout: 45000 });
  await expect(assistant.getByRole("region", { name: /GraphRAG evidence/i })).toBeVisible();
  await expect(assistant.locator(".agent-evidence-item").first()).toContainText(/Neighborhood Food Pantry|pantry/i);

  const firstDocId = await firstEvidenceDocId(assistant);
  expect(firstDocId).toBe("svc-food-pantry-1");

  await sendAssistantMessage(assistant, `save service ${firstDocId}`);
  const confirmation = assistant.getByRole("region", { name: /Confirmation required: Save service/i });
  await expect(confirmation).toBeVisible({ timeout: 15000 });
  await expect(confirmation).toContainText(firstDocId);
  await expect(confirmation.getByText(/Before/i)).toBeVisible();
  await expect(confirmation.getByText(/After/i)).toBeVisible();
  await expect(assistant.getByText(new RegExp(`^Saved service ${escapeRegex(firstDocId)}\\.$`))).toHaveCount(0);

  await confirmation.getByRole("button", { name: /Confirm Save service/i }).click();
  await expect(assistant.getByText(new RegExp(`^Saved service ${escapeRegex(firstDocId)}\\.$`)).first()).toBeVisible({
    timeout: 45000,
  });
});

test("assistant launchers expose separate text and voice chat surfaces", async ({ page }) => {
  await enterSignedInApp(page);

  const launcher = visibleClosedLauncher(page);
  await expect(launcher.getByRole("button", { name: /Open text chat/i })).toBeVisible();
  await expect(launcher.getByRole("button", { name: /Open voice chat/i })).toBeVisible();

  await launcher.getByRole("button", { name: /Open voice chat/i }).click();
  const voiceAssistant = visibleVoiceAssistant(page);
  await expect(voiceAssistant).toBeVisible();
  await expect(voiceAssistant.getByRole("button", { name: /Start voice chat/i })).toBeVisible();
  await expect(voiceAssistant.getByText(/Voice chat/i).first()).toBeVisible();

  await voiceAssistant.getByRole("button", { name: /Close voice chat|Close voice assistant|Close assistant/i }).first().click();
  await openTextAssistant(page);
  await expect(visibleAssistant(page).getByLabel(/Message Abby assistant/i)).toBeVisible();
});

test("front page assistant button opens voice chat", async ({ page }) => {
  await page.goto("/");
  await clearPwaState(page);
  await page.goto("/");

  await page.getByRole("button", { name: /Open assistant/i }).click();
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible({ timeout: 10000 });

  const voiceAssistant = visibleVoiceAssistant(page);
  await expect(voiceAssistant).toBeVisible();
  await expect(voiceAssistant.getByRole("button", { name: /Start voice chat/i })).toBeVisible();
});

test("voice chat shows local audio model warmup progress", async ({ page }) => {
  await installFakeAudioWorker(page);
  await enterSignedInApp(page);

  await visibleClosedLauncher(page).getByRole("button", { name: /Open voice chat/i }).click();
  const voiceAssistant = visibleVoiceAssistant(page);
  const progressRegion = voiceAssistant.getByRole("status", { name: /Audio model progress/i });

  await expect(progressRegion).toBeVisible({ timeout: 5000 });
  await expect(progressRegion.getByText(/Downloading model|Loading runtime|Warming up/i)).toBeVisible();
  await expect(progressRegion.locator(".agent-audio-model-progress-header span")).toHaveText("38%");
  await expect(progressRegion.getByText(/decoder_model_quantized\.onnx/i)).toBeVisible();
});

function visibleAssistant(page: Page): Locator {
  return page.locator('aside[aria-label="Abby text assistant"]:visible, aside[aria-label="Abby assistant"]:visible');
}

function visibleVoiceAssistant(page: Page): Locator {
  return page.locator('aside[aria-label="Abby voice assistant"]:visible, aside[aria-label="Abby assistant"]:visible');
}

function visibleClosedLauncher(page: Page): Locator {
  return page.locator(".agent-chat-launcher:visible, .agent-chat-bottom-launcher:visible").first();
}

async function openTextAssistant(page: Page): Promise<void> {
  await visibleClosedLauncher(page).getByRole("button", { name: /Open text chat/i }).click();
}

async function enterSignedInApp(page: Page): Promise<void> {
  await page.goto("/");
  await clearPwaState(page);
  await page.goto("/");
  if (await page.getByRole("heading", { name: /Sign in to Abby/i }).isVisible()) {
    await page.getByRole("button", { name: /Open assistant/i }).click();
  }
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible({ timeout: 10000 });
  await closeAssistantIfOpen(page);
}

async function closeAssistantIfOpen(page: Page): Promise<void> {
  const closeButton = page
    .getByRole("button", { name: /Close text chat|Close voice chat|Close voice assistant|Close assistant/i })
    .first();
  if (await closeButton.isVisible()) {
    await closeButton.click();
  }
}

async function clearPwaState(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const registrations = "serviceWorker" in navigator ? await navigator.serviceWorker.getRegistrations() : [];
    await Promise.all(registrations.map((registration) => registration.unregister()));
    if ("caches" in window) {
      await Promise.all((await caches.keys()).map((cacheName) => caches.delete(cacheName)));
    }
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
}

async function installFakeAudioWorker(page: Page): Promise<void> {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "gpu", {
      configurable: true,
      value: {},
    });

    const RealWorker = window.Worker;
    class FakeAudioWorker {
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: ErrorEvent) => void) | null = null;
      private readonly realWorker?: Worker;

      constructor(scriptUrl: string | URL, options?: WorkerOptions) {
        if (!String(scriptUrl).includes("clientAudioWorker")) {
          this.realWorker = new RealWorker(scriptUrl, options);
          return this.realWorker;
        }
      }

      postMessage(message: { id: string; type: string; data?: { modelName?: string } }) {
        const modelName = message.data?.modelName || "LiquidAI/LFM2.5-Audio-1.5B-ONNX";
        window.setTimeout(() => {
          this.onmessage?.({
            data: {
              id: message.id,
              type: "progress",
              progress: {
                phase: "loading-runtime",
                progress: 4,
                status: "Loading LiquidAI audio runtime.",
                modelName,
              },
            },
          } as MessageEvent);
        }, 25);
        window.setTimeout(() => {
          this.onmessage?.({
            data: {
              id: message.id,
              type: "progress",
              progress: {
                phase: "downloading-model",
                progress: 38,
                status: "Downloading audio model decoder_model_quantized.onnx.",
                file: "decoder_model_quantized.onnx",
                modelName,
              },
            },
          } as MessageEvent);
        }, 50);
      }

      terminate() {
        this.realWorker?.terminate();
      }
    }

    Object.defineProperty(window, "Worker", {
      configurable: true,
      value: FakeAudioWorker,
    });
  });
}

async function installTiny211Corpus(page: Page): Promise<void> {
  const documents = [
    {
      doc_id: "svc-food-pantry-1",
      doc_type: "service",
      title: "Neighborhood Food Pantry",
      text: "Neighborhood Food Pantry provides food boxes, pantry appointments, and grocery pickup help in Portland.",
      text_truncated: false,
      source_url: "https://211.example.test/food-pantry",
      source_content_cid: "bafy-food-pantry-1",
      source_page_cid: "bafy-food-page-1",
      provider_name: "Neighborhood Food Pantry",
      program_name: "Pantry appointments",
      categories: "Food",
      host: "211.example.test",
      city: "Portland",
      state: "OR",
    },
    {
      doc_id: "svc-meals-1",
      doc_type: "service",
      title: "Community Meal Site",
      text: "Community Meal Site serves prepared meals and referral support in Portland.",
      text_truncated: false,
      source_url: "https://211.example.test/meals",
      source_content_cid: "bafy-meals-1",
      source_page_cid: "bafy-meals-page-1",
      provider_name: "Community Meal Site",
      program_name: "Prepared meals",
      categories: "Food",
      host: "211.example.test",
      city: "Portland",
      state: "OR",
    },
  ];
  const bm25 = {
    schemaVersion: 1,
    documents: [
      {
        doc_id: "svc-food-pantry-1",
        doc_type: "service",
        source_url: "https://211.example.test/food-pantry",
        source_content_cid: "bafy-food-pantry-1",
        source_page_cid: "bafy-food-page-1",
        document_length: 12,
        terms: { food: 3, pantry: 4, portland: 1, grocery: 1 },
        term_idf: { food: 2.1, pantry: 2.8, portland: 0.7, grocery: 1.2 },
      },
      {
        doc_id: "svc-meals-1",
        doc_type: "service",
        source_url: "https://211.example.test/meals",
        source_content_cid: "bafy-meals-1",
        source_page_cid: "bafy-meals-page-1",
        document_length: 9,
        terms: { food: 1, meals: 3, portland: 1 },
        term_idf: { food: 2.1, meals: 1.6, portland: 0.7 },
      },
    ],
    documentFrequency: { food: 2, pantry: 1, portland: 2, grocery: 1, meals: 1 },
    k1: 1.2,
    b: 0.75,
    avgdl: 10.5,
    documentCount: 2,
    maxTermsPerDocument: 8,
  };

  await page.route("**/corpus/211-info/current/generated/documents.json", async (route) => {
    await route.fulfill({ json: documents });
  });
  await page.route("**/corpus/211-info/current/generated/bm25-documents.json", async (route) => {
    await route.fulfill({ json: bm25 });
  });
}

async function sendAssistantMessage(assistant: Locator, message: string): Promise<void> {
  const composer = assistant.getByLabel(/Message Abby assistant/i);
  await expect(composer).toBeEnabled({ timeout: 45000 });
  await composer.fill(message);
  await assistant.getByRole("button", { name: /Send assistant message/i }).click();
}

async function firstEvidenceDocId(assistant: Locator): Promise<string> {
  const firstEvidenceItem = assistant.locator(".agent-evidence-item").first();
  await expect(firstEvidenceItem).toBeVisible();
  return (await firstEvidenceItem.locator("dl div").filter({ hasText: "Doc ID" }).locator("dd").innerText()).trim();
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
