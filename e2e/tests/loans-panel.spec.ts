import { expect, test } from "@playwright/test";

import { LIBRARIAN, READER, csrfToken, loginAs } from "./helpers";

// Idempotent like SHARED_BOOK: first run creates the book, later runs take
// the 409 path, so the pinned catalogue counts only move 28 -> 29 once.
const TITLE = "UI Panel Book";
const AUTHOR = "UI Author";
const BOOK_CODE = "UIP-BOOK-01";
const COPY_CODE = "UIP-BOOK-02";

test("panel add, reader checkout and librarian return through the UI", async ({
  page,
  request,
}) => {
  // Heal-first on the shared library_e2e database (aborted runs may leave
  // our codes checked out); mirrors circulation.spec.ts.
  await loginAs(request, LIBRARIAN);
  for (const code of [BOOK_CODE, COPY_CODE]) {
    const stale = await request.get(`/api/v1/staff/loans/?inventory_code=${code}`);
    expect(stale.status()).toBe(200);
    for (const open of await stale.json()) {
      const cleanup = await request.post(`/api/v1/loans/${open.id}/return/`, {
        data: {},
        headers: { "X-CSRFToken": await csrfToken(request) },
      });
      expect(cleanup.status()).toBe(200);
    }
  }

  // Librarian signs in through the account UI — lands on the panel.
  await page.goto("/konto/");
  await page.locator("#login-username").fill(LIBRARIAN.username);
  await page.locator("#login-password").fill(LIBRARIAN.password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page).toHaveURL("/panel/");

  // Librarian adds the book through the panel UI (201, or 409 when it exists).
  await page.goto("/panel/");
  await page.locator("#book-title").fill(TITLE);
  await page.locator("#book-author").fill(AUTHOR);
  await page.locator("#book-code").fill(BOOK_CODE);
  await page.getByRole("button", { name: "Dodaj książkę" }).click();
  await expect(page.locator("#book-message")).toContainText(/Dodano książkę|zajęty/);

  // Resolve the book id through the API (the UI reads it from the catalogue).
  const found = await request.get(`/api/v1/books/?q=${encodeURIComponent(TITLE)}`);
  expect(found.status()).toBe(200);
  const existing = (await found.json()).results.find(
    (b: { title: string }) => b.title === TITLE,
  );
  expect(existing).toBeDefined();

  // Librarian adds the second copy through the panel UI.
  await page.locator("#copy-book-id").fill(String(existing.id));
  await page.locator("#copy-code").fill(COPY_CODE);
  await page.getByRole("button", { name: "Dodaj egzemplarz" }).click();
  await expect(page.locator("#copy-message")).toContainText(/Dodano egzemplarz|zajęty/);

  // Catalogue shows both copies available.
  await page.goto("/");
  await page.getByLabel("Szukaj").fill(TITLE);
  await page.getByRole("button", { name: "Szukaj" }).click();
  await expect(page.getByText(`${TITLE} — ${AUTHOR} (dostępne: 2/2)`)).toBeVisible();

  // Reader signs in and checks out the copy through the loans UI.
  await page.goto("/konto/");
  await page.locator("#login-username").fill(READER.username);
  await page.locator("#login-password").fill(READER.password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page).toHaveURL("/wypozyczenia/");

  await page.goto("/wypozyczenia/");
  await page.locator("#inventory-code").fill(COPY_CODE);
  await page.getByRole("button", { name: "Wypożycz" }).click();
  await expect(page.locator("#checkout-message")).toHaveText("Wypożyczono.");
  await expect(page.locator("#loans").getByText(COPY_CODE)).toBeVisible();

  // A second checkout of the same copy is refused, in Polish.
  await page.locator("#inventory-code").fill(COPY_CODE.toLowerCase());
  await page.getByRole("button", { name: "Wypożycz" }).click();
  await expect(page.locator("#checkout-message")).toHaveText(
    "Ten egzemplarz jest już wypożyczony.",
  );

  // Librarian finds and returns it through the panel UI.
  await page.goto("/konto/");
  await page.locator("#login-username").fill(LIBRARIAN.username);
  await page.locator("#login-password").fill(LIBRARIAN.password);
  await page.getByRole("button", { name: "Zaloguj" }).click();
  await expect(page).toHaveURL("/panel/");
  await page.locator("#lookup-code").fill(COPY_CODE);
  await page.getByRole("button", { name: "Znajdź" }).click();
  await expect(page.locator("#lookup-message")).toHaveText(
    "Znaleziono otwarte wypożyczenie.",
  );
  await page.getByRole("button", { name: "Zwróć" }).click();
  await expect(page.locator("#lookup-message")).toHaveText("Zwrócono.");
  await page.locator("#lookup-code").fill(COPY_CODE);
  await page.getByRole("button", { name: "Znajdź" }).click();
  await expect(page.locator("#lookup-message")).toHaveText("Brak otwartego wypożyczenia.");
});
