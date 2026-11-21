import { expect, test } from "@playwright/test";

test("OI-019: E-STOP sends before the operator console starts", async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.sentCommands = [];
    class TestSocket {
      static OPEN = 1;
      readyState = 0;
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      constructor() {
        queueMicrotask(() => {
          this.readyState = 1;
          this.onopen?.();
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
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Start operator console" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /E-STOP/ }).click();
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([{ command: "estop", confirmed: false }]);
});
