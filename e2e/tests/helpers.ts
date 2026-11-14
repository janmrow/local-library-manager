import { APIRequestContext, expect } from "@playwright/test";

export const LIBRARIAN = { username: "librarian", password: "librarian12345" };
export const READER = { username: "reader", password: "reader12345" };

// One book shared by librarian.spec.ts and circulation.spec.ts through the
// persistent library_e2e database. Rename here, never in a single spec:
// the specs pin each other's assumptions (counts, availability).
export const SHARED_BOOK = {
  title: "E2E Librarian Book",
  author: "E2E Author",
  bookCode: "E2E-LIB-01",
  copyCode: "E2E-LIB-02",
};

export async function csrfToken(request: APIRequestContext): Promise<string> {
  const state = await request.storageState();
  const cookie = state.cookies.find((c) => c.name === "csrftoken");
  if (!cookie) throw new Error("missing csrftoken cookie");
  return cookie.value;
}

export async function loginAs(
  request: APIRequestContext,
  account: { username: string; password: string },
): Promise<string> {
  await request.get("/api/v1/session/");
  const anonymousToken = await csrfToken(request);
  const login = await request.post("/api/v1/session/", {
    data: account,
    headers: { "X-CSRFToken": anonymousToken },
  });
  expect(login.status()).toBe(200);
  return csrfToken(request);
}

export async function ensureBookId(
  request: APIRequestContext,
  token: string,
  title: string,
  author: string,
  code: string,
): Promise<number> {
  const create = await request.post("/api/v1/books/", {
    data: { title, author, inventory_code: code },
    headers: { "X-CSRFToken": token },
  });
  if (create.status() === 201) return (await create.json()).id;
  expect(create.status()).toBe(409);
  const found = await request.get(`/api/v1/books/?q=${encodeURIComponent(title)}`);
  expect(found.status()).toBe(200);
  const existing = (await found.json()).results.find(
    (b: { title: string }) => b.title === title,
  );
  expect(existing).toBeDefined();
  return existing.id;
}
