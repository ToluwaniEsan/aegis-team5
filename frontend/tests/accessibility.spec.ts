import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import * as fixtures from "../src/mock/fixtures.generated";
import type { Snapshot } from "../src/contracts/ui";

async function loadFixture(
  page: import("@playwright/test").Page,
  data: Snapshot,
) {
  await page.addInitScript((snapshot) => {
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
      close() {
        this.onclose?.();
      }
      send() {}
    }
    Object.defineProperty(window, "WebSocket", { value: TestSocket });
  }, data);
  await page.goto("/");
  await page.getByRole("button", { name: "Start operator console" }).click();
  await expect(page.getByLabel("Payload status")).toBeVisible();
}

for (const [name, snapshot] of Object.entries(fixtures)) {
  test(`ENV_002_no_scroll_${name}`, async ({ page }) => {
    await loadFixture(page, snapshot);
    const size = await page.evaluate(() => ({
      width: document.scrollingElement!.scrollWidth,
      height: document.scrollingElement!.scrollHeight,
    }));
    expect(size.width).toBeLessThanOrEqual(1366);
    expect(size.height).toBeLessThanOrEqual(768);
  });

  test(`OI_019_estop_visible_${name}`, async ({ page }) => {
    await loadFixture(page, snapshot);
    const button = page.getByRole("button", { name: /E-STOP/i }).first();
    await expect(button).toBeVisible();
    await expect(button).toBeEnabled();
    await expect(button).toBeInViewport({ ratio: 1 });
  });

  test(`OI_018_grayscale_${name}`, async ({ page }) => {
    await loadFixture(page, snapshot);
    await page.addStyleTag({ content: "html { filter: grayscale(1); }" });
    const directory = path.resolve(process.cwd(), "../reports/grayscale");
    await mkdir(directory, { recursive: true });
    await page.screenshot({ path: path.join(directory, `${name}.png`) });
  });
}
