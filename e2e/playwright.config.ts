import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // Serial files: specs share one persistent library_e2e database and pin
  // catalogue counts, so parallel workers would race each other's writes.
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8001",
  },
  webServer: {
    command:
      "uv run --project .. --env-file ../.env --locked python ../manage.py runserver 127.0.0.1:8001 --noreload",
    url: "http://127.0.0.1:8001/api/v1/books/",
    reuseExistingServer: false,
    env: {
      ...process.env,
      DB_NAME: "library_e2e",
      APP_ENV: "e2e",
    } as Record<string, string>,
  },
});
