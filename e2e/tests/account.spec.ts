import { expect, test } from "@playwright/test";

import { READER } from "./helpers";

test("account register, login and logout through the UI", async ({ page }) => {
  const username = `uitest${Date.now()}`;
  const password = "UiTest12345";

  await page.goto("/konto/");
  await expect(page.getByRole("heading", { name: "Konto" })).toBeVisible();

  // Wrong password stays Polish, never a raw backend detail.
  await page.locator("#login-username").fill(READER.username);
  await page.locator("#login-password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page.locator("#login-error")).toHaveText("Nieprawidłowy login lub hasło.");

  // Register a fresh reader.
  await page.locator("#register-username").fill(username);
  await page.locator("#register-password").fill(password);
  await page.getByRole("button", { name: "Utwórz konto" }).click();
  await expect(page.locator("#register-error")).toHaveText(
    "Konto utworzone — możesz się zalogować.",
  );

  // Sign in as the new reader.
  await page.locator("#login-username").fill(username);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page.locator("#account-status")).toHaveText(`Zalogowano jako ${username}.`);

  // Sign out back to guest.
  await page.getByRole("button", { name: "Wyloguj" }).click();
  await expect(page.locator("#account-status")).toHaveText(
    "Gość — zaloguj się lub utwórz konto.",
  );
});
