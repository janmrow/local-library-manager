import { expect, test } from "@playwright/test";

import {
  LIBRARIAN,
  READER,
  SHARED_BOOK,
  csrfToken,
  ensureBookId,
  loginAs,
} from "./helpers";

// Shared with librarian.spec.ts: this flow creates no books of its own, so the
// pinned catalogue counts never drift. Runs serially (workers: 1) with the
// other files against the shared library_e2e database.
const TITLE = SHARED_BOOK.title;
const AUTHOR = SHARED_BOOK.author;
const BOOK_CODE = SHARED_BOOK.bookCode;

test("reader checkout followed by librarian return", async ({ page, request }) => {
  let token = await loginAs(request, LIBRARIAN);
  await ensureBookId(request, token, TITLE, AUTHOR, BOOK_CODE);

  token = await loginAs(request, READER);
  let checkout = await request.post("/api/v1/loans/", {
    data: { inventory_code: BOOK_CODE.toLowerCase() },
    headers: { "X-CSRFToken": token },
  });
  if (checkout.status() === 409) {
    // A previous aborted run left the copy checked out: return it, retry.
    token = await loginAs(request, LIBRARIAN);
    const stale = await request.get(
      `/api/v1/staff/loans/?inventory_code=${BOOK_CODE}`,
    );
    expect(stale.status()).toBe(200);
    const [open] = await stale.json();
    expect(open, "expected the stale open loan after 409").toBeDefined();
    const cleanup = await request.post(`/api/v1/loans/${open.id}/return/`, {
      data: {},
      headers: { "X-CSRFToken": token },
    });
    expect(cleanup.status()).toBe(200);
    token = await loginAs(request, READER);
    checkout = await request.post("/api/v1/loans/", {
      data: { inventory_code: BOOK_CODE },
      headers: { "X-CSRFToken": token },
    });
  }
  expect(checkout.status()).toBe(201);
  const loan = await checkout.json();
  expect(loan).toMatchObject({ inventory_code: BOOK_CODE, returned_at: null });
  expect(checkout.headers()["location"]).toBe(`/api/v1/loans/${loan.id}/`);
  expect(checkout.headers()["cache-control"]).toBe("no-store");

  const mine = await request.get("/api/v1/loans/");
  expect(mine.status()).toBe(200);
  expect((await mine.json()).map((l: { id: number }) => l.id)).toContain(loan.id);

  token = await loginAs(request, LIBRARIAN);
  const found = await request.get(
    `/api/v1/staff/loans/?inventory_code=${BOOK_CODE.toLowerCase()}`,
  );
  expect(found.status()).toBe(200);
  expect(await found.json()).toMatchObject([{ id: loan.id }]);

  const returned = await request.post(`/api/v1/loans/${loan.id}/return/`, {
    data: {},
    headers: { "X-CSRFToken": token },
  });
  expect(returned.status()).toBe(200);
  const stamp = (await returned.json()).returned_at;
  expect(stamp).not.toBeNull();

  const retry = await request.post(`/api/v1/loans/${loan.id}/return/`, {
    data: {},
    headers: { "X-CSRFToken": await csrfToken(request) },
  });
  expect(retry.status()).toBe(200);
  expect((await retry.json()).returned_at).toBe(stamp);

  const gone = await request.get(
    `/api/v1/staff/loans/?inventory_code=${BOOK_CODE}`,
  );
  expect(gone.status()).toBe(200);
  expect(await gone.json()).toEqual([]);

  await page.goto("/");
  await page.getByLabel("Szukaj").fill(TITLE);
  await page.getByRole("button", { name: "Szukaj" }).click();
  // Scope to the TITLE row: a body-wide first match could pass on 0/0 or on
  // a stale row rendered before the search finishes.
  const row = page.getByText(new RegExp(`${TITLE}.*dostępne: (\\d+)\\/(\\d+)`));
  await expect(row).toBeVisible();
  const match = (await row.textContent())?.match(/dostępne: (\d+)\/(\d+)/);
  expect(match).not.toBeNull();
  expect(match?.[1]).toBe(match?.[2]);
  expect(Number(match?.[1])).toBeGreaterThan(0);
});
