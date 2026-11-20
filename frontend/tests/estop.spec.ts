import { expect, test } from "@playwright/test";

declare global {
  interface Window {
    sentCommands: unknown[];
  }
}

test("OI-019: E-STOP sends while a dialog is open", async ({ page }) => {
  await page.addInitScript(() => {
    window.sentCommands = [];
    class TestSocket {
      static OPEN = 1;
      readyState = 0;
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      constructor() {
        queueMicrotask(() => {
          this.readyState = TestSocket.OPEN;
          this.onopen?.();
        });
      }
      send(message: string) {
        window.sentCommands.push(JSON.parse(message));
      }
      close() {
        this.readyState = 3;
        this.onclose?.();
      }
    }
    Object.defineProperty(window, "WebSocket", { value: TestSocket });
  });
  await page.goto("/");
  await page.evaluate(() => {
    const dialog = document.createElement("div");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-label", "Test overlay");
    Object.assign(dialog.style, {
      position: "fixed",
      top: "0",
      right: "0",
      bottom: "0",
      left: "0",
      zIndex: "1",
      background: "var(--panel)",
    });
    document.body.appendChild(dialog);
  });
  const estop = page.getByRole("button", { name: /E-STOP/ });
  expect(await estop.boundingBox()).toMatchObject({ width: 152, height: 44 });
  await estop.click();
  await expect
    .poll(() => page.evaluate(() => window.sentCommands))
    .toMatchObject([
      { kind: "command", command: "estop", args: {}, confirmed: false },
    ]);
});
