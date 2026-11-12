import { expect, test } from "@playwright/test";

test("browse catalogue from the database", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Katalog" })).toBeVisible();
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
  await expect(page.getByText("Extra Book 00 — E2E Author (dostępne: 1/1)")).toBeVisible();
  await expect(page.getByText("Znaleziono: 27")).toBeVisible();
  await expect(page.getByRole("button", { name: "Następna" })).toBeEnabled();
});

test("search filters the catalogue", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
  await page.getByLabel("Szukaj").fill("lem");
  await page.getByRole("button", { name: "Szukaj" }).click();
  await expect(page.getByText("Solaris")).toBeVisible();
  await expect(page.getByText("Dune")).toBeHidden();
  await expect(page.getByText("Znaleziono: 1")).toBeVisible();
});

test("pagination reaches the last result", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Znaleziono: 27")).toBeVisible();
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Następna" })).toBeEnabled();
  await page.getByRole("button", { name: "Następna" }).click();
  await expect(page.getByText("Extra Book 24")).toBeVisible();
  await expect(page.getByText("Solaris — Stanisław Lem (dostępne: 1/1)")).toBeVisible();
  await page.getByRole("button", { name: "Poprzednia" }).click();
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
});

test("a slower earlier search does not overwrite a newer one", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
  let delayedOnce = false;
  let releaseFirst!: () => void;
  const firstHeld = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  await page.route("**/api/v1/books/*", async (route) => {
    if (!delayedOnce) {
      delayedOnce = true;
      await firstHeld;
    }
    await route.continue();
  });
  const newerResponse = page.waitForResponse((resp) => resp.url().includes("q=lem"));
  const olderResponse = page.waitForResponse((resp) => resp.url().includes("q=herbert"));
  await page.getByLabel("Szukaj").fill("herbert");
  await page.getByRole("button", { name: "Szukaj" }).click();
  await page.getByLabel("Szukaj").fill("lem");
  await page.getByRole("button", { name: "Szukaj" }).click();
  await newerResponse;
  await expect(page.getByText("Solaris — Stanisław Lem (dostępne: 1/1)")).toBeVisible();
  releaseFirst();
  await olderResponse;
  await expect(page.getByText("Solaris — Stanisław Lem (dostępne: 1/1)")).toBeVisible();
  await expect(page.getByText("Dune")).toBeHidden();
  await expect(page.getByText("Znaleziono: 1")).toBeVisible();
});

test("pagination stays disabled while loading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Dune — Frank Herbert (dostępne: 1/1)")).toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/books/*", async (route) => {
    await gate;
    await route.continue();
  });
  await page.getByLabel("Szukaj").fill("lem");
  await page.getByRole("button", { name: "Szukaj" }).click();
  await expect(page.getByRole("button", { name: "Następna" })).toBeDisabled();
  release();
  await page.waitForResponse((resp) => resp.url().includes("q=lem"));
  await expect(page.getByText("Solaris — Stanisław Lem (dostępne: 1/1)")).toBeVisible();
  await expect(page.getByText("Znaleziono: 1")).toBeVisible();
});
