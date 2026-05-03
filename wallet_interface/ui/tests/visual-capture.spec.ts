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
      "Emergency contacts must be the first primary card.",
      "Social services must be the second primary card.",
      "The next check-in status should be easy to find without crowding the cards."
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
      "The CAPTCHA placeholder and profile review should be visible and understandable."
    ]
  },
  {
    id: "register-filled",
    path: "/#/register",
    title: "Registration flow with profile draft",
    state: "filled form",
    goals: [
      "Filled required and optional fields should remain readable.",
      "The review panel should summarize entered information clearly.",
      "The submit action should visually communicate whether the profile is complete."
    ],
    prepare: async (page) => {
      const screen = page.locator(".screen");
      await page.getByLabel(/Legal or full name/i).fill("Abby Example");
      await page.getByLabel(/Preferred name/i).fill("Abby");
      await page.getByLabel(/Birth date/i).fill("1990-01-01");
      await page.getByLabel(/Account photo/i).setInputFiles({
        name: "abby-profile.png",
        mimeType: "image/png",
        buffer: Buffer.from("iVBORw0KGgo=", "base64")
      });
      await page.getByLabel(/Phone/i).fill("(503) 555-0100");
      await page.getByLabel(/Email/i).fill("abby@example.org");
      await page.getByLabel(/Current safe location/i).fill("Downtown shelter area");
      await page.getByLabel(/Shelter affiliation/i).fill("Rose City Shelter");
      await screen.getByRole("button", { name: "Shelter" }).click();
      await screen.getByRole("button", { name: "Benefits" }).click();
      await page.getByLabel(/Bot check complete/i).check();
    }
  },
  {
    id: "check-in",
    path: "/#/check-in",
    title: "Check-in setup",
    state: "default",
    goals: [
      "The 30-day maximum interval constraint should be clear.",
      "Reminder channels and next check-in date should be easy to scan.",
      "The primary check-in action should be reachable on mobile."
    ]
  },
  {
    id: "check-in-maximum-interval",
    path: "/#/check-in",
    title: "Check-in setup at maximum interval",
    state: "30 day interval",
    goals: [
      "The maximum allowed interval should still feel safe and understandable.",
      "Grace period and escalation explanation should remain visible.",
      "The next check-in preview should update without visual confusion."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Interval days/i).fill("30");
      await page.getByLabel(/Grace period hours/i).fill("12");
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
      "Recipient type selection should clearly support social workers and agencies."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Name or agency/i).fill("Morgan Caseworker");
      await page.getByLabel(/Relationship or role/i).fill("Outreach case worker");
      await page.getByLabel(/Phone/i).fill("(503) 555-0188");
      await page.getByLabel(/Email/i).fill("morgan@example.org");
      await page.getByLabel(/Type/i).selectOption("social_worker");
    }
  },
  {
    id: "sharing-rules",
    path: "/#/sharing-rules",
    title: "Disclosure rules",
    state: "default",
    goals: [
      "No recipient should appear to receive access by default.",
      "Scope labels should be understandable to non-technical users.",
      "The page should make different recipient scopes visually comparable."
    ]
  },
  {
    id: "uploads",
    path: "/#/uploads",
    title: "Document and information vault",
    state: "default",
    goals: [
      "Upload affordance should work for camera/mobile and desktop file upload.",
      "Private versus sharing-eligible status should be visually distinct.",
      "Sensitive documents should not look implicitly shared."
    ]
  },
  {
    id: "social-services",
    path: "/#/social-services",
    title: "Social services",
    state: "default",
    goals: [
      "Service categories should be dense enough to scan but not cramped.",
      "The government-services liaison entry point should be visible.",
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
      await page.getByLabel(/Confirm user is present/i).check();
      await page.getByLabel(/Clear browser data/i).check();
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
      "The next action for contacting a liaison should be clear."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Access code/i).fill("123456");
      await page.getByLabel(/Recipient phone or email/i).fill("maya@example.org");
      await page.getByRole("button", { name: /Verify and view/i }).click();
    }
  },
  {
    id: "benefits-protection",
    path: "/#/benefits-protection",
    title: "Benefits protection opt-in",
    state: "default",
    goals: [
      "The opt-in should not look enabled by default.",
      "Agency action should not be implied as guaranteed.",
      "Legal/policy review limitations should be visible without overwhelming the user."
    ]
  },
  {
    id: "benefits-protection-enabled",
    path: "/#/benefits-protection",
    title: "Benefits protection opt-in enabled",
    state: "checked",
    goals: [
      "The checked consent state should be visually explicit.",
      "Legal and policy limitations should remain visible after opt-in.",
      "The save action should become available without implying guaranteed agency action."
    ],
    prepare: async (page) => {
      await page.getByLabel(/Allow Abby to prepare/i).check();
    }
  },
  {
    id: "analytics",
    path: "/#/analytics",
    title: "Analytics consent",
    state: "default",
    goals: [
      "Derived fields should be clearly separated from raw personal records.",
      "Privacy thresholds and budget limits should be understandable.",
      "Opt-in controls should not imply participation by default."
    ]
  },
  {
    id: "analytics-consented",
    path: "/#/analytics",
    title: "Analytics consent selected study",
    state: "one study consented",
    goals: [
      "The consented study should be visually distinct from paused or available studies.",
      "Derived field badges should remain visible after opt-in.",
      "Privacy budget and cohort threshold should stay prominent."
    ],
    prepare: async (page) => {
      const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
      await housingStudy.getByRole("checkbox").check();
    }
  }
];

const artifactRoot = path.resolve(process.cwd(), "artifacts/ui-screenshots/latest");

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

test("capture Abby UI screenshots for multimodal UX review", async ({ page }, testInfo) => {
  const viewport = projectSlug(testInfo.project.name);
  const viewportDir = path.join(artifactRoot, viewport);
  await fs.rm(viewportDir, { force: true, recursive: true });
  await fs.mkdir(viewportDir, { recursive: true });

  const manifest: ScreenshotManifestEntry[] = [];

  for (const route of captureScenarios) {
    if (!scenarioMatchesViewport(route, viewport)) {
      continue;
    }
    await page.goto(route.path);
    await expect(page.locator(".screen")).toBeVisible();
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
