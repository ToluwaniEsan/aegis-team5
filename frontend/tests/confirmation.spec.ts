import { expect, test } from "@playwright/test";
import travelling from "../src/test-fixtures/travelling.json" with { type: "json" };

test("OI-003 and OI-019: real confirmation keyboard and E-STOP", async ({
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
  }, travelling);
  await page.goto("/");
  await page.getByRole("button", { name: "Start operator console" }).click();
  await page.getByRole("button", { name: "Abort", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Confirm command" });
  await expect(dialog).toBeVisible();
  expect((await dialog.boundingBox())!.width).toBe(480);
  await expect(dialog.getByRole("button", { name: "Cancel" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Abort mission" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  expect(await page.evaluate(() => window.sentCommands)).toEqual([]);
  await page.getByRole("button", { name: /E-STOP/ }).click();
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([{ command: "estop", confirmed: false }]);
  await dialog.getByRole("button", { name: "Abort mission" }).focus();
  await page.keyboard.press("Space");
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([
      { command: "estop", confirmed: false },
      { command: "abort", confirmed: true },
    ]);
});
