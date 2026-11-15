// Shared fetch helper for the server-rendered pages.
// GET reads JSON; POST/DELETE send CSRF from the csrftoken cookie.

export function getCookie(name) {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

export function getCsrfToken() {
  return getCookie("csrftoken");
}

export class ApiError extends Error {
  constructor(path, status, body) {
    super(`${path} failed with ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function parseBody(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function request(path, options) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
  });
  if (response.status === 204) return null;
  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(path, response.status, body);
  }
  return body;
}

export async function apiGet(path) {
  return request(path, { headers: { Accept: "application/json" } });
}

export async function apiPost(path, data) {
  return request(path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken() ?? "",
    },
    body: JSON.stringify(data ?? {}),
  });
}

export async function apiDelete(path) {
  return request(path, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      "X-CSRFToken": getCsrfToken() ?? "",
    },
  });
}

export async function fetchSession() {
  return apiGet("/api/v1/session/");
}
