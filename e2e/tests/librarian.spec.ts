import { expect, test } from "@playwright/test";

import { LIBRARIAN, READER, SHARED_BOOK, csrfToken, ensureBookId } from "./helpers";

const TITLE = SHARED_BOOK.title;
const BOOK_CODE = SHARED_BOOK.bookCode;
const COPY_CODE = SHARED_BOOK.copyCode;

test("librarian catalogue changes via API", async ({ page, request }) => {
  await request.get("/api/v1/session/");
  const anonymousToken = await csrfToken(request);

  const login = await request.post("/api/v1/session/", {
    data: LIBRARIAN,
    headers: { "X-CSRFToken": anonymousToken },
  });
  expect(login.status()).toBe(200);
  expect(await login.json()).toMatchObject({
    authenticated: true,
    username: "librarian",
    is_librarian: true,
  });
  const librarianToken = await csrfToken(request);
  expect(librarianToken).not.toBe(anonymousToken);

  const bookId = await ensureBookId(request, librarianToken, TITLE, "E2E Author", BOOK_CODE);

  const copy = await request.post(`/api/v1/books/${bookId}/copies/`, {
    data: { inventory_code: COPY_CODE },
    headers: { "X-CSRFToken": await csrfToken(request) },
  });
  expect([201, 409]).toContain(copy.status());

  // Heal stale open loans left by an aborted circulation run; without this
  // the availability assertion below would see 1/2 on a dirty database.
  // Loud on purpose: healing must stay an exception, not routine.
  const healed: number[] = [];
  for (const code of [BOOK_CODE, COPY_CODE]) {
    const stale = await request.get(
      `/api/v1/staff/loans/?inventory_code=${code}`,
    );
    expect(stale.status()).toBe(200);
    for (const open of await stale.json()) {
      const cleanup = await request.post(`/api/v1/loans/${open.id}/return/`, {
        data: {},
        headers: { "X-CSRFToken": await csrfToken(request) },
      });
      expect(cleanup.status()).toBe(200);
      healed.push(open.id);
    }
  }
  if (healed.length > 0) console.log(`healed stale loans: ${healed}`);
  expect(healed.length).toBeLessThanOrEqual(1);

  const detail = await request.get(`/api/v1/books/${bookId}/`);
  expect(await detail.json()).toMatchObject({
    title: TITLE,
    total_copies: 2,
    available_copies: 2,
  });

  const before = await (await request.get("/api/v1/books/")).json();
  const readerLogin = await request.post("/api/v1/session/", {
    data: READER,
    headers: { "X-CSRFToken": await csrfToken(request) },
  });
  expect(readerLogin.status()).toBe(200);
  expect(await readerLogin.json()).toMatchObject({
    authenticated: true,
    username: "reader",
    is_librarian: false,
  });
  const denied = await request.post("/api/v1/books/", {
    data: { title: "Nope", author: "Nope", inventory_code: "E2E-DENIED" },
    headers: { "X-CSRFToken": await csrfToken(request) },
  });
  expect(denied.status()).toBe(403);
  expect((await denied.json()).code).toBe("forbidden");
  const after = await (await request.get("/api/v1/books/")).json();
  expect(after.count).toBe(before.count);

  await page.goto("/");
  await page.getByLabel("Szukaj").fill(TITLE);
  await page.getByRole("button", { name: "Szukaj" }).click();
  await expect(page.getByText(`${TITLE} — E2E Author (dostępne: 2/2)`)).toBeVisible();
});
