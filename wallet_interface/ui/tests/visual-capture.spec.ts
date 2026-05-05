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
    id: "home",
    path: "/",
    title: "Two-card home screen",
    state: "default",
    goals: [
      "Contacts and Sharing should be the only overview cards.",
      "The combined next check-in and Check in now action should live in Quick actions.",
      "The next check-in status should be easy to find without crowding the overview cards."
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
      "Recipients should be scannable with verification and scope status.",
      "Adding a recipient should not require horizontal scrolling.",
      "Removal controls should not visually dominate the emergency setup task."
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
      "Recipient type selection should clearly support emergency contacts, social workers, police precincts, shelter staff, government help, and benefits agencies."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Name or group/i).fill("Morgan Caseworker");
      await page.getByLabel(/Relationship or role/i).fill("Outreach case worker");
      await page.getByLabel("Phone", { exact: true }).fill("(503) 555-0188");
      await page.getByLabel("Email", { exact: true }).fill("morgan@example.org");
      await page.getByLabel(/Type/i).selectOption("social_worker");
    }
  },
  {
    id: "sharing-rules",
    path: "/#/sharing-rules",
    title: "Sharing choices",
    state: "default",
    goals: [
      "All sharing choices should start checked when no saved choice exists.",
      "It should be clear that the user can turn off any item before saving.",
      "Scope labels should be short, plain, and useful to screen-reader users."
    ]
  },
  {
    id: "sharing-rules-some-items-off",
    path: "/#/sharing-rules",
    title: "Sharing choices with items turned off",
    state: "medical and housing items off",
    goals: [
      "Unchecked items should be visually clear but not alarming.",
      "The preview should update to plain item names after choices change.",
      "The legal review note should remain visible after opt-out choices."
    ],
    prepare: async (page) => {
      const recipient = page.locator(".scope-editor").filter({ hasText: "Maya Johnson" });
      await recipient.getByLabel(/Medical notes/i).uncheck();
      await recipient.getByLabel(/Found permanent housing/i).uncheck();
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
      const nudge = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach Shelter" }).first();
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
    id: "recipient-access",
    path: "/#/recipient-access",
    title: "Emergency recipient access",
    state: "unverified",
    goals: [
      "Sensitive data should be hidden before verification.",
      "Recipient verification should be prominent and clear.",
      "The screen should be usable in the field on a phone."
    ]
  },
  {
    id: "recipient-access-verified",
    path: "/#/recipient-access",
    title: "Emergency recipient access after verification",
    state: "verified",
    goals: [
      "Authorized disclosure scopes should be obvious after verification.",
      "The screen should not expose unrelated wallet data.",
      "The next action for contacting support should be clear."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Access code/i).fill("123456");
      await page.getByLabel(/Recipient phone or email/i).fill("maya@example.org");
      await page.getByRole("button", { name: /Verify and view/i }).click();
    }
  },
  {
    id: "recipient-access-approval-ready",
    path: "/#/recipient-access",
    title: "Recipient access ready for approval",
    state: "second approval recorded",
    goals: [
      "The request should clearly show that enough approvals are recorded.",
      "Approve and reject actions should remain easy to distinguish.",
      "Capability language should stay understandable before sharing starts."
    ],
    prepare: async (page) => {
      const request = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach" });
      await request.getByRole("button", { name: /Record approval/i }).click();
      await expect(request.getByText(/2\/2 approvals/i)).toBeVisible();
    }
  },
  {
    id: "recipient-access-active-grant",
    path: "/#/recipient-access",
    title: "Recipient access active grant",
    state: "grant approved",
    goals: [
      "Approved access should be visually distinct from pending requests.",
      "The revoke action should be visible without overpowering the receipt details.",
      "Sharing history should show the approved grant clearly."
    ],
    prepare: async (page) => {
      const request = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach" });
      await request.getByRole("button", { name: /Record approval/i }).click();
      await request.getByRole("button", { name: /^Approve$/i }).click();
      await expect(page.getByRole("article", { name: /Downtown Outreach/i }).filter({ hasText: "Share proof code" })).toBeVisible();
    }
  },
  {
    id: "recipient-access-grant-revoked",
    path: "/#/recipient-access",
    title: "Recipient access revoked grant",
    state: "grant revoked",
    goals: [
      "Revoked access should be obvious without hiding the audit trail.",
      "The screen should explain that access is turned off.",
      "Receipt status should remain readable on mobile."
    ],
    prepare: async (page) => {
      const request = page.locator(".access-request-item").filter({ hasText: "Legal Aid desk" });
      await request.getByRole("button", { name: /Revoke/i }).click();
      await expect(request.getByText("revoked", { exact: true })).toBeVisible();
    }
  },
  {
    id: "benefits-protection",
    path: "/#/benefits-protection",
    title: "Benefits protection consent",
    state: "default",
    goals: [
      "The benefits checkbox should start checked unless the user saved it as off.",
      "The user should be able to turn it off in plain language.",
      "Agency action should not be implied as guaranteed.",
      "Legal/policy review limitations should be visible without overwhelming the user."
    ]
  },
  {
    id: "benefits-protection-enabled",
    path: "/#/benefits-protection",
    title: "Benefits protection consent enabled",
    state: "checked",
    goals: [
      "The checked consent state should be visually explicit.",
      "Legal and policy limitations should remain visible after consent is on.",
      "The save action should become available without implying guaranteed agency action."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Allow Abby to prepare/i).check();
    }
  },
  {
    id: "benefits-protection-off",
    path: "/#/benefits-protection",
    title: "Benefits protection consent off",
    state: "unchecked",
    goals: [
      "Turning benefits help off should be visibly clear.",
      "The copy should still avoid promising agency action.",
      "The privacy/legal review caveat should remain visible."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Allow Abby to prepare/i).uncheck();
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
const routeReadyHeadings: Record<string, RegExp> = {
  "/": /Your safety plan/i,
  "/#/analytics": /Share group facts, not your name/i,
  "/#/benefits-protection": /Benefits notice/i,
  "/#/check-in": /Set your schedule/i,
  "/#/contacts": /People who can help/i,
  "/#/exports": /Shareable wallet bundles/i,
  "/#/proof-center": /Verified wallet claims/i,
  "/#/recipient-access": /Requests to see my info/i,
  "/#/register": /Create your Abby profile/i,
  "/#/security": /Account safety/i,
  "/#/sharing-rules": /Choose what each person can see/i,
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
