import { expect, test } from "@playwright/test";
import fault from "../src/mock/fixtures/fault_shift.json" with { type: "json" };

test("OI-008: payload and stale fault health cards fit the screen", async ({
  page,
}) => {
  const snapshot = {
    ...fault,
    vehicle_health: {
      ...fault.vehicle_health,
      overall: "FAULT",
      subsystems: fault.vehicle_health.subsystems.map((item, index) => ({
        ...item,
        stale: true,
        age_s: 12,
        ...(index === 0 ? { status: "FAULT", detail: "Battery fault" } : {}),
      })),
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
  const panel = page.getByLabel("Payload and vehicle health");
  const payload = page.getByLabel("Payload status");
  const health = page.getByLabel("Vehicle health", { exact: true });
  await expect(health.getByText("Battery fault")).toBeVisible();
  await expect(health.getByText(/Hatched rows are OUT OF DATE/)).toBeVisible();
  await expect(health.locator(".health-stale")).toHaveCount(5);
  const [panelBox, payloadBox, healthBox] = await Promise.all([
    panel.boundingBox(),
    payload.boundingBox(),
    health.boundingBox(),
  ]);
  expect(healthBox!.y).toBeGreaterThanOrEqual(
    payloadBox!.y + payloadBox!.height,
  );
  expect(healthBox!.y + healthBox!.height).toBeLessThanOrEqual(
    panelBox!.y + panelBox!.height,
  );
  expect(
    await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    })),
  ).toEqual({ width: 1366, height: 768 });
  for (const row of await health.locator(".health-row").all()) {
    expect(
      await row.evaluate(
        (element) => element.scrollWidth <= element.clientWidth,
      ),
    ).toBe(true);
  }
});
