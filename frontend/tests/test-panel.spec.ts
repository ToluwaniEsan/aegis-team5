import { expect, test } from "@playwright/test";
import idle from "../src/test-fixtures/idle.json" with { type: "json" };

test("GEN-001: test panel injects and keeps E-STOP available", async ({
  page,
}) => {
  await page.addInitScript((snapshot) => {
    window.sentCommands = [];
    class TestSocket {
      static OPEN = 1;
      readyState = 0;
      onopen: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      onclose: (() => void) | null = null;
      constructor() {
        queueMicrotask(() => {
          this.readyState = 1;
          this.onopen?.();
          this.onmessage?.({ data: JSON.stringify(snapshot) });
        });
      }
      send(data: string) {
        window.sentCommands.push(JSON.parse(data));
      }
      close() {
        this.onclose?.();
      }
    }
    Object.defineProperty(window, "WebSocket", { value: TestSocket });
  }, idle);
  let injection: unknown;
  await page.route("**/api/test/inject", async (route) => {
    injection = route.request().postDataJSON();
    await route.fulfill({ json: { msg_id: "injected" } });
  });
  await page.goto("/test");
  await page.getByLabel("Shift (cm)").fill("3.1");
  await page.getByRole("button", { name: "Inject shift" }).click();
  await expect(page.getByText("Inject shift: sent · injected")).toBeVisible();
  expect(injection).toEqual({
    target: "payload",
    action: "shift",
    params: { cm: 3.1 },
  });
  await page
    .getByRole("heading", { name: "LAST 10 RESULTS" })
    .scrollIntoViewIfNeeded();
  await expect(page.getByRole("button", { name: /E-STOP/ })).toBeInViewport();
  await page.getByRole("button", { name: /E-STOP/ }).click();
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([{ command: "estop", confirmed: false }]);
});
