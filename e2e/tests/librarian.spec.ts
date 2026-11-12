import { APIRequestContext, expect, test } from "@playwright/test";

const LIBRARIAN = { username: "librarian", password: "librarian12345" };
const READER = { username: "reader", password: "reader12345" };
const TITLE = "E2E Librarian Book";
const BOOK_CODE = "E2E-LIB-01";
const COPY_CODE = "E2E-LIB-02";

async function csrfToken(request: APIRequestContext): Promise<string> {
  const state = await request.storageState();
  const cookie = state.cookies.find((c) => c.name === "csrftoken");
  if (!cookie) throw new Error("missing csrftoken cookie");
  return cookie.value;
}

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

  const headers = { "X-CSRFToken": librarianToken };
  let bookId: number;
  const create = await request.post("/api/v1/books/", {
    data: { title: TITLE, author: "E2E Author", inventory_code: BOOK_CODE },
    headers,
  });
  if (create.status() === 201) {
    bookId = (await create.json()).id;
  } else {
    expect(create.status()).toBe(409);
    const found = await request.get(`/api/v1/books/?q=${encodeURIComponent(TITLE)}`);
    expect(found.status()).toBe(200);
    const results = (await found.json()).results;
    expect(results.length).toBeGreaterThan(0);
    bookId = results[0].id;
  }

  const copy = await request.post(`/api/v1/books/${bookId}/copies/`, {
    data: { inventory_code: COPY_CODE },
    headers: { "X-CSRFToken": await csrfToken(request) },
  });
  expect([201, 409]).toContain(copy.status());

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
