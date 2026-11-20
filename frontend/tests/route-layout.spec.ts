import { expect, test } from "@playwright/test";
import travelling from "../src/mock/fixtures/travelling.json" with { type: "json" };

test("OI-012: blocked route and labels fit the 1366 × 768 panel", async ({
  page,
}) => {
  const nav = travelling.nav;
  const snapshot = {
    ...travelling,
    nav: {
      ...nav,
      blocked: {
        at: nav.route[0],
        old_route: nav.route,
        reason: "Bridge out",
        new_eta_s: 500,
        since: travelling.server_time,
      },
    },
  };
  await page.addInitScript((data) => {
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
          this.onmessage?.({ data: JSON.stringify(data) });
        });
      }
      close() {
        this.onclose?.();
      }
    }
    Object.defineProperty(window, "WebSocket", { value: TestSocket });
  }, snapshot);
  await page.goto("/");
  const map = page.getByRole("img", { name: "Schematic route" });
  await expect(map).toBeVisible();
  await expect(page.getByText("CAUTION · ROUTE BLOCKED")).toBeVisible();
  const mapBox = (await map.boundingBox())!;
  for (const label of ["FOB Alpha", "Outpost Bravo"]) {
    const box = (await map.getByText(label).boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(mapBox.x);
    expect(box.x + box.width).toBeLessThanOrEqual(mapBox.x + mapBox.width);
  }
  const panel = (await page
    .getByLabel("Route and navigation", { exact: true })
    .boundingBox())!;
  const values = (await page.locator(".navigation-values").boundingBox())!;
  expect(values.y + values.height).toBeLessThanOrEqual(panel.y + panel.height);
  expect(
    await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    })),
  ).toEqual({ width: 1366, height: 768 });
});
