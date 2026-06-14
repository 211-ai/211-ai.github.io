import { expect, test, type Locator, type Page } from "@playwright/test";

test("assistant opens, searches food pantry evidence, navigates, and gates saving", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible({ timeout: 10000 });
  await installTiny211Corpus(page);

  await page.getByRole("button", { name: /Open assistant/i }).click();
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

function visibleAssistant(page: Page): Locator {
  return page.locator('aside[aria-label="Abby assistant"]:visible');
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
