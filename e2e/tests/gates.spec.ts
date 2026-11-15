import { expect, test } from "@playwright/test";

import { LIBRARIAN, READER } from "./helpers";

// Regression for the exploratory findings: guests and readers get a guided
// gate (not a dead form), and copy creation validates the book id in Polish.
// Read-only: no books, copies or loans are created here.
test("guest on loans page sees disabled form with login link", async ({
  page,
}) => {
  await page.goto("/wypozyczenia/");
  await expect(page.locator("#checkout-gate")).toBeVisible();
  await expect(page.locator("#checkout-gate a")).toHaveAttribute("href", "/konto/");
  await expect(page.getByRole("button", { name: "Wypożycz" })).toBeDisabled();
  await expect(page.locator("#loans-status")).toHaveText(
    "Aby zobaczyć wypożyczenia, zaloguj się.",
  );
});

test("reader on staff panel sees permission gate", async ({ page }) => {
  await page.goto("/konto/");
  await page.locator("#login-username").fill(READER.username);
  await page.locator("#login-password").fill(READER.password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page).toHaveURL("/wypozyczenia/");
  await page.goto("/panel/");
  await expect(page.locator("#staff-gate")).toHaveText(
    `Zalogowano jako ${READER.username} — to konto nie ma uprawnień bibliotekarza.`,
  );
  await expect(page.getByRole("button", { name: "Dodaj książkę" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Znajdź" })).toBeDisabled();
});

test("copy form rejects non-numeric book id in Polish", async ({ page }) => {
  await page.goto("/konto/");
  await page.locator("#login-username").fill(LIBRARIAN.username);
  await page.locator("#login-password").fill(LIBRARIAN.password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page).toHaveURL("/panel/");
  await page.locator("#copy-book-id").fill("abc");
  await page.locator("#copy-code").fill("LL-999");
  await page.getByRole("button", { name: "Dodaj egzemplarz" }).click();
  await expect(page.locator("#copy-message")).toHaveText(
    "Podaj numeryczne ID książki z Katalogu.",
  );
});
