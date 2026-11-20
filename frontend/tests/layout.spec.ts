import { expect, test } from '@playwright/test';

test('ENV-002: five panel grid fits the 1366 by 768 viewport', async ({ page }) => {
  await page.goto('/');
  const expected = [
    ['Top bar', 0, 0, 1366, 64],
    ['Payload and vehicle health', 0, 64, 420, 544],
    ['Route and navigation', 420, 64, 526, 544],
    ['Mission controls', 946, 64, 420, 544],
    ['Alerts and delivery', 0, 608, 1366, 160],
  ] as const;
  for (const [name, x, y, width, height] of expected) {
    const region = page.getByLabel(name, { exact: true });
    await expect(region).toBeVisible();
    expect(await region.boundingBox()).toEqual({ x, y, width, height });
  }
  expect(await page.evaluate(() => ({ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }))).toEqual({ width: 1366, height: 768 });
});

test('ENV-002: smaller windows show the size requirement', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 768 });
  await page.goto('/');
  await expect(page.getByText('Increase the window size to at least 1366 × 768.')).toBeVisible();
  await expect(page.locator('#app')).toBeHidden();
});
