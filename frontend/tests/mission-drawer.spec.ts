import { expect, test } from "@playwright/test";
import idle from "../src/mock/fixtures/idle.json" with { type: "json" };

test("OI-019: E-STOP sends while the mission drawer is open", async ({
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
  await page.goto("/");
  await page.getByRole("button", { name: "New mission" }).click();
  const drawer = page.getByRole("dialog", { name: "Mission form" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByLabel("Origin")).toBeFocused();
  const box = (await drawer.boundingBox())!;
  expect(box.y).toBe(64);
  expect(box.x + box.width).toBe(1366);
  expect(
    await drawer.evaluate(
      (element) => element.scrollHeight <= element.clientHeight,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    })),
  ).toEqual({ width: 1366, height: 768 });
  await page.getByRole("button", { name: /E-STOP/ }).click();
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([
      { kind: "command", command: "estop", args: {}, confirmed: false },
    ]);
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(page.getByRole("button", { name: "New mission" })).toBeFocused();
});
