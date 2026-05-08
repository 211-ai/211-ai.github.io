import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

type CaptureScenario = {
  id: string;
  path: string;
  title: string;
  state: string;
  viewportOnly?: "desktop" | "mobile";
  goals: string[];
  prepare?: (page: Page) => Promise<void>;
};

type CaptureViewport = "desktop" | "mobile";

type ScreenshotManifestEntry = Omit<CaptureScenario, "prepare"> & {
  viewport: CaptureViewport;
  screenshotPath: string;
  multimodalPrompt: string;
};

const captureScenarios: CaptureScenario[] = [
  {
    id: "login",
    path: "/__login",
    title: "Login page",
    state: "signed out",
    goals: [
      "Username and password fields should be immediately visible.",
      "The sign-in action should be clear and reachable on mobile.",
      "The page should feel like the entry point to Abby without extra informational boxes."
    ]
  },
  {
    id: "home",
    path: "/",
    title: "Home safety plan screen",
    state: "default",
    goals: [
      "The welcome heading should be the first clear page signal.",
      "The old overview card row should stay removed.",
      "The next check-in and Check in now action should live in Quick actions."
    ]
  },
  {
    id: "mobile-navigation-open",
    path: "/",
    title: "Mobile navigation menu",
    state: "menu open",
    viewportOnly: "mobile",
    goals: [
      "The menu should expose all major routes without crowding.",
      "The current route should be visually indicated.",
      "Navigation labels should be clear enough for repeated mobile use."
    ],
    prepare: async (page) => {
      await page.getByRole("button", { name: /Open menu/i }).click();
    }
  },
  {
    id: "register",
    path: "/#/register",
    title: "Registration flow",
    state: "empty",
    goals: [
      "Required fields should be obvious without feeling punitive.",
      "Optional sensitive fields should feel clearly optional.",
      "The photo or photo ID field should allow image files and PDFs without promising a thumbnail preview.",
      "The bot-check controls should be visible and understandable."
    ]
  },
  {
    id: "register-filled",
    path: "/#/register",
    title: "Registration flow with profile draft",
    state: "filled form",
    goals: [
      "Filled required and optional fields should remain readable.",
      "The selected photo or photo ID file should be clear without showing an image or PDF thumbnail.",
      "Identity details should read as a separate group from later fill-in fields."
    ],
    prepare: async (page) => {
      const screen = page.locator(".screen");
      await page.getByLabel(/Legal or full name/i).fill("Abby Example");
      await page.getByLabel(/Preferred name/i).fill("Abby");
      await page.getByLabel(/Pronouns/i).fill("they/them");
      await page.getByLabel(/Birth date/i).fill("1990-01-01");
      await page.getByLabel(/Photo or photo ID/i).setInputFiles({
        name: "abby-id.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4\n")
      });
      await page.getByLabel(/Phone/i).fill("(503) 555-0100");
      await page.getByLabel(/Email/i).fill("abby@example.org");
      await page.getByLabel(/Current safe location/i).fill("Downtown shelter area");
      await page.getByLabel(/Preferred shelter/i).fill("Rose City Shelter");
      await screen.getByRole("button", { name: "Shelter" }).click();
      await screen.getByRole("button", { name: "Benefits" }).click();
      await page.getByLabel(/Quick health check complete/i).check();
      await page.getByLabel(/Bot check complete/i).check();
    }
  },
  {
    id: "register-invalid-file",
    path: "/#/register",
    title: "Registration unsupported photo or ID file",
    state: "unsupported file selected",
    goals: [
      "Unsupported file feedback should be clear and close to the file field.",
      "The form should not show a selected-file preview or thumbnail.",
      "The error state should not crowd required identity fields on mobile."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Photo or photo ID/i).setInputFiles({
        name: "abby-id.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("not accepted")
      });
      await expect(page.getByText(/We can't use this file/i)).toBeVisible();
    }
  },
  {
    id: "check-in",
    path: "/#/check-in",
    title: "Check-in setup",
    state: "default",
    goals: [
      "The 30-day check-in limit should be clear.",
      "Reminder channels and next check-in date should be easy to scan.",
      "The primary check-in action should be reachable on mobile."
    ]
  },
  {
    id: "check-in-maximum-interval",
    path: "/#/check-in",
    title: "Check-in setup at 30 days",
    state: "30 day interval",
    goals: [
      "The longest allowed interval should still feel safe and understandable.",
      "The missed check-in help-step explanation should remain visible.",
      "The next check-in preview should update without visual confusion."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Days between check-ins/i).fill("30");
      await page.getByLabel(/Extra hours after a missed check-in/i).fill("12");
    }
  },
  {
    id: "check-in-email-warning",
    path: "/#/check-in",
    title: "Check-in unavailable method warning",
    state: "email check-in unavailable",
    goals: [
      "The warning should tell the user what to do next.",
      "Disabled or unavailable methods should be understandable without relying on color.",
      "Check-in controls should remain reachable after the warning appears."
    ],
    prepare: async (page) => {
      await page.getByRole("button", { name: /Check in by email/i }).click();
      await expect(page.getByText(/Email is off|Add an email/i)).toBeVisible();
    }
  },
  {
    id: "contacts",
    path: "/#/contacts",
    title: "Emergency contacts",
    state: "default",
    goals: [
      "The add shelter or group area should appear before saved contacts.",
      "The add person form should show sharing choices before saving.",
      "Saved contacts should appear underneath the add controls and stay easy to scan."
    ]
  },
  {
    id: "contacts-add-recipient-draft",
    path: "/#/contacts",
    title: "Emergency contacts add-recipient form",
    state: "draft recipient",
    goals: [
      "The add-recipient form should be easy to complete on mobile.",
      "Contact method fields should fit and remain labeled.",
      "The new-person sharing checkboxes should be visible and readable before save."
    ],
    prepare: async (page) => {
      await page.getByLabel(/First name/i).fill("Morgan");
      await page.getByLabel(/Last name/i).fill("Caseworker");
      await page.getByLabel(/Relationship or role/i).fill("Outreach case worker");
      await page.getByLabel("Phone", { exact: true }).fill("(503) 555-0188");
      await page.getByLabel("Email", { exact: true }).fill("morgan@example.org");
      await page.getByLabel(/Type/i).selectOption("social_worker");
    }
  },
  {
    id: "contacts-add-person-sharing-some-off",
    path: "/#/contacts",
    title: "Emergency contacts add-recipient form with sharing off",
    state: "draft recipient with medical and housing sharing off",
    goals: [
      "Unchecked sharing choices should be visible without feeling scary.",
      "The form should still fit cleanly on mobile after several fields are filled.",
      "The user should be able to review choices before adding the person."
    ],
    prepare: async (page) => {
      await page.getByLabel(/First name/i).fill("Morgan");
      await page.getByLabel(/Last name/i).fill("Caseworker");
      await page.getByLabel(/Relationship or role/i).fill("Outreach case worker");
      await page.getByLabel("Phone", { exact: true }).fill("(503) 555-0188");
      await page.getByLabel("Email", { exact: true }).fill("morgan@example.org");
      await page.getByLabel(/Type/i).selectOption("social_worker");
      await page.getByLabel(/Medical notes/i).uncheck();
      await page.getByLabel(/Found permanent housing/i).uncheck();
    }
  },
  {
    id: "contacts-edit-sharing",
    path: "/#/contacts",
    title: "Emergency contacts edit sharing panel",
    state: "saved contact sharing editor open",
    goals: [
      "A saved contact should open into an obvious sharing edit panel.",
      "Checkboxes should have a clear group heading and readable labels.",
      "Save and cancel actions should be reachable without horizontal scrolling."
    ],
    prepare: async (page) => {
      const savedMaya = page.locator(".recipient-list-item").filter({ hasText: "Maya Johnson" });
      await savedMaya.getByRole("button", { name: /^Edit sharing$/i }).click();
      await expect(savedMaya.getByRole("region", { name: /Edit sharing for Maya Johnson/i })).toBeVisible();
    }
  },
  {
    id: "contacts-edit-sharing-some-off",
    path: "/#/contacts",
    title: "Emergency contacts edit sharing panel with choices off",
    state: "saved contact medical and housing sharing off",
    goals: [
      "Unchecked saved-contact sharing choices should be visually clear.",
      "The selected-count badge should update near the panel heading.",
      "The edit panel should remain compact enough for mobile review."
    ],
    prepare: async (page) => {
      const savedMaya = page.locator(".recipient-list-item").filter({ hasText: "Maya Johnson" });
      await savedMaya.getByRole("button", { name: /^Edit sharing$/i }).click();
      const editPanel = savedMaya.getByRole("region", { name: /Edit sharing for Maya Johnson/i });
      await editPanel.getByLabel(/Medical notes/i).uncheck();
      await editPanel.getByLabel(/Found permanent housing/i).uncheck();
      await expect(editPanel.getByText("9 selected", { exact: true })).toBeVisible();
    }
  },
  {
    id: "contacts-shelter-nudge-approved",
    path: "/#/contacts",
    title: "Emergency contacts after shelter nudge approval",
    state: "shelter nudge approved",
    goals: [
      "Approving a shelter nudge should add the shelter without implying broad sharing.",
      "The added shelter should be easy to find in the contact list.",
      "The request history should remain understandable after approval."
    ],
    prepare: async (page) => {
      const addContactSection = page.getByRole("region", { name: "Add contact" });
      await addContactSection.getByRole("radio", { name: /Shelter or group/i }).check();
      const nudge = addContactSection.locator(".access-request-item").filter({ hasText: "Downtown Outreach Shelter" }).first();
      await nudge.getByRole("button", { name: /^Approve$/i }).click();
      await expect(page.locator(".recipient-list-item").filter({ hasText: "Downtown Outreach Shelter" })).toBeVisible();
    }
  },
  {
    id: "uploads",
    path: "/#/uploads",
    title: "Saved files and info",
    state: "default",
    goals: [
      "Upload affordance should work for camera/mobile and desktop file upload.",
      "Private versus sharing-eligible status should be visually distinct.",
      "The vault should not show or ask for a document sensitivity level."
    ]
  },
  {
    id: "uploads-new-file",
    path: "/#/uploads",
    title: "Saved files after adding a document",
    state: "new file added",
    goals: [
      "The newly added file should be visible without exposing document contents.",
      "Private versus share-eligible status should remain easy to scan.",
      "The upload area should still be available after a file is added."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Choose file to upload/i).setInputFiles({
        name: "benefits-update.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4\n")
      });
      await expect(page.getByText(/benefits-update\.pdf/i)).toBeVisible();
    }
  },
  {
    id: "social-services",
    path: "/#/social-services",
    title: "Social services",
    state: "default",
    goals: [
      "Service categories should be dense enough to scan but not cramped.",
      "The government-services help entry point should be visible.",
      "Matched services should be easy to compare on mobile and desktop."
    ]
  },
  {
    id: "shelter",
    path: "/#/shelter",
    title: "Shelter portal",
    state: "default",
    goals: [
      "Shelter staff workflows should feel separate from personal account controls.",
      "Shared-device safety should be explicit.",
      "The portal should support low-bandwidth, repeated-use contexts."
    ]
  },
  {
    id: "shelter-shared-device-checklist",
    path: "/#/shelter",
    title: "Shelter portal shared-device checklist",
    state: "safety checklist checked",
    goals: [
      "Checked safety steps should be visually clear.",
      "Staff audit responsibility should remain visible.",
      "The workflow should still feel usable on a shared device."
    ],
    prepare: async (page) => {
      const checklist = page.locator(".checklist input");
      await checklist.nth(0).check();
      await checklist.nth(1).check();
    }
  },
  {
    id: "shelter-create-user-draft",
    path: "/#/shelter",
    title: "Shelter portal create-user draft",
    state: "staff-created user draft",
    goals: [
      "Staff-created user fields should stay separate from shared-device safety controls.",
      "Photo or ID PDF support should be clear without a preview.",
      "Contact reminder helper copy should remain readable in the staff flow."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Verified staff operator/i).selectOption({ label: "Avery Patel" });
      const createUser = page.locator('section[aria-labelledby="Create-user-account"]');
      await createUser.getByLabel(/Legal or full name/i).fill("Casey Example");
      await createUser.getByLabel(/Preferred name/i).fill("Casey");
      await createUser.getByLabel(/Email/i).fill("casey@example.org");
      await createUser.getByLabel(/Photo or photo ID/i).setInputFiles({
        name: "casey-id.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4\n")
      });
      await expect(createUser.getByText(/Selected file: casey-id\.pdf/i)).toBeVisible();
    }
  },
  {
    id: "analytics",
    path: "/#/analytics",
    title: "Group facts choice",
    state: "default",
    goals: [
      "Group facts choices should start checked unless the user saved them as off.",
      "The user should be able to turn off each available choice in plain language.",
      "Safe detail badges should be clearly separated from personal records.",
      "Group size and privacy-left limits should be understandable."
    ]
  },
  {
    id: "analytics-consented",
    path: "/#/analytics",
    title: "Group facts selected study",
    state: "one choice on",
    goals: [
      "The selected choice should be visually distinct from paused or available choices.",
      "Safe detail badges should remain visible after consent is on.",
      "Privacy-left and group-size limits should stay prominent."
    ],
    prepare: async (page) => {
      const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
      await housingStudy.getByRole("checkbox").check();
    }
  },
  {
    id: "analytics-one-choice-off",
    path: "/#/analytics",
    title: "Group facts choice with one option off",
    state: "one choice off",
    goals: [
      "The off choice should be visually clear without making the user feel punished.",
      "Available and paused choices should remain easy to compare.",
      "Group size and privacy-left labels should remain visible."
    ],
    prepare: async (page) => {
      const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
      await housingStudy.getByRole("checkbox").uncheck();
    }
  },
  {
    id: "proof-center",
    path: "/#/proof-center",
    title: "Proof center",
    state: "default",
    goals: [
      "Proof creation controls should not imply private data is shown.",
      "Public proof inputs should be scannable.",
      "API-required state should be clear but not alarming."
    ]
  },
  {
    id: "exports",
    path: "/#/exports",
    title: "Export center",
    state: "default",
    goals: [
      "Export bundle creation should communicate that records stay encrypted.",
      "Recipient and record fields should fit on mobile.",
      "Existing export status should be easy to scan."
    ]
  },
  {
    id: "security",
    path: "/#/security",
    title: "Security settings",
    state: "default",
    goals: [
      "Security preferences should read as saved settings, not temporary reveal controls.",
      "Shared-device guidance should be visible without exposing sensitive data.",
      "Bot check copy should make prototype limits clear."
    ]
  },
  {
    id: "security-customized",
    path: "/#/security",
    title: "Security settings with wallet persistence",
    state: "default wallet safety tools",
    goals: [
      "The layout should remain easy to scan on mobile.",
      "Wallet backup controls should not imply local-only preferences are production enforcement.",
      "Security tool tiles should be understandable without extra instructions."
    ]
  },
  {
    id: "audit",
    path: "/#/audit",
    title: "Audit history",
    state: "default",
    goals: [
      "Consent and access history should be easy to scan.",
      "Audit entries should show actor and timestamp clearly.",
      "The screen should not expose more sensitive detail than needed."
    ]
  }
];

const artifactRoot = path.resolve(process.cwd(), "artifacts/ui-screenshots/latest");
const appSessionKey = "abby-ui-session-v1";
const routeReadyHeadings: Record<string, RegExp> = {
  "/": /Welcome to your safety plan!/i,
  "/#/analytics": /Share group facts, not your name/i,
  "/#/check-in": /Set your schedule/i,
  "/#/contacts": /People who can help/i,
  "/#/exports": /Shareable wallet bundles/i,
  "/#/proof-center": /Verified wallet claims/i,
  "/#/register": /Create your Abby profile/i,
  "/#/security": /Account safety/i,
  "/#/shelter": /Assisted access/i,
  "/#/social-services": /Find support/i,
  "/#/uploads": /Saved files and info/i,
  "/#/audit": /Consent and access history/i
};

function projectSlug(projectName: string): CaptureViewport {
  return projectName.toLowerCase().includes("mobile") ? "mobile" : "desktop";
}

function scenarioMatchesViewport(route: CaptureScenario, viewport: CaptureViewport) {
  if (!route.viewportOnly) return true;
  return viewport === route.viewportOnly;
}

function buildPrompt(route: CaptureScenario, viewport: CaptureViewport) {
  return [
    `Review the Abby UI screenshot for: ${route.title}.`,
    `Viewport: ${viewport}.`,
    `State: ${route.state}.`,
    "Prioritize mobile/desktop usability, accessibility, safety, privacy clarity, visual hierarchy, and text fit.",
    "Return concise findings grouped as: critical issues, UI/UX improvements, accessibility concerns, and suggested implementation changes.",
    "Route-specific goals:",
    ...route.goals.map((goal) => `- ${goal}`)
  ].join("\n");
}

async function openCaptureScenario(page: Page, scenarioPath: string) {
  if (scenarioPath === "/__login") {
    await page.goto("/");
    await page.evaluate((key) => window.localStorage.removeItem(key), appSessionKey);
    await page.reload();
    await expect(page.locator(".login-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Sign in/i })).toBeVisible();
    return;
  }

  await page.goto("/");
  await page.evaluate(
    (key) => window.localStorage.setItem(key, JSON.stringify({ username: "visual-reviewer" })),
    appSessionKey
  );

  if (scenarioPath === "/#/shelter") {
    await verifyShelterStaffForCapture(page);
    return;
  }
  await page.goto(scenarioPath);
  await page.reload();
  await expect(page.locator(".screen")).toBeVisible();
  await expect(page.getByRole("heading", { name: routeReadyHeadings[scenarioPath] })).toBeVisible();
}

async function verifyShelterStaffForCapture(page: Page) {
  await page.goto("/#/register");
  await expect(page.getByRole("heading", { name: /Create your Abby profile/i })).toBeVisible();
  await page.getByLabel(/I am shelter staff/i).check();
  await page.locator("select").first().selectOption("Rose City Shelter");
  await page.getByLabel(/Shelter staff PIN/i).fill("1234");
  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/Shelter staff verified/i)).toBeVisible();
  await page.goto("/#/shelter");
  await expect(page.getByRole("heading", { name: /Assisted access/i })).toBeVisible();
}

test("capture Abby UI screenshots for multimodal UX review", async ({ page }, testInfo) => {
  test.setTimeout(240000);
  const viewport = projectSlug(testInfo.project.name);
  const viewportDir = path.join(artifactRoot, viewport);
  await fs.rm(viewportDir, { force: true, recursive: true });
  await fs.mkdir(viewportDir, { recursive: true });

  const manifest: ScreenshotManifestEntry[] = [];

  for (const route of captureScenarios) {
    if (!scenarioMatchesViewport(route, viewport)) {
      continue;
    }
    await openCaptureScenario(page, route.path);
    if (route.prepare) {
      await route.prepare(page);
    }
    await page.screenshot({
      fullPage: true,
      path: path.join(viewportDir, `${route.id}.png`)
    });

    manifest.push({
      id: route.id,
      path: route.path,
      title: route.title,
      state: route.state,
      goals: route.goals,
      viewport,
      screenshotPath: path.relative(process.cwd(), path.join(viewportDir, `${route.id}.png`)),
      multimodalPrompt: buildPrompt(route, viewport)
    });
  }

  const manifestPath = path.join(viewportDir, "manifest.json");
  await fs.writeFile(manifestPath, `${JSON.stringify({ generatedAt: new Date().toISOString(), screenshots: manifest }, null, 2)}\n`);
});
