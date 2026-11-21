import type { LatLon } from "./contracts/ui";

export type Point = { x: number; y: number };
export const ROUTE_WIDTH = 500;
export const ROUTE_HEIGHT = 330;
export const ROUTE_MARGIN = 24;

export function projectPoints(points: LatLon[]): Point[] {
  if (!points.length) return [];
  const minX = Math.min(...points.map((p) => p.lon));
  const maxX = Math.max(...points.map((p) => p.lon));
  const minY = Math.min(...points.map((p) => p.lat));
  const maxY = Math.max(...points.map((p) => p.lat));
  const dx = maxX - minX;
  const dy = maxY - minY;
  const scale = Math.min(
    dx ? (ROUTE_WIDTH - 2 * ROUTE_MARGIN) / dx : Infinity,
    dy ? (ROUTE_HEIGHT - 2 * ROUTE_MARGIN) / dy : Infinity,
  );
  const safeScale = Number.isFinite(scale) ? scale : 1;
  return points.map((p) => ({
    x: ROUTE_WIDTH / 2 + (p.lon - (minX + maxX) / 2) * safeScale,
    y: ROUTE_HEIGHT / 2 - (p.lat - (minY + maxY) / 2) * safeScale,
  }));
}

export function travelledPoints(
  route: Point[],
  progress: number | null,
): Point[] {
  if (progress === null || route.length < 2) return [];
  const lengths = route
    .slice(1)
    .map((point, index) =>
      Math.hypot(point.x - route[index].x, point.y - route[index].y),
    );
  let remaining =
    (lengths.reduce((sum, length) => sum + length, 0) *
      Math.max(0, Math.min(100, progress))) /
    100;
  const result = [route[0]];
  for (let index = 0; index < lengths.length; index++) {
    const length = lengths[index];
    if (length === 0) continue;
    const fraction = Math.min(1, remaining / length);
    const start = route[index];
    const end = route[index + 1];
    result.push({
      x: start.x + (end.x - start.x) * fraction,
      y: start.y + (end.y - start.y) * fraction,
    });
    remaining -= length * fraction;
    if (fraction < 1) break;
  }
  return result;
}

export function routeHeading(route: Point[], position: Point): number | null {
  let bestDistance = Infinity;
  let heading: number | null = null;
  for (let index = 1; index < route.length; index++) {
    const a = route[index - 1];
    const b = route[index];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lengthSquared = dx * dx + dy * dy;
    if (!lengthSquared) continue;
    const t = Math.max(
      0,
      Math.min(
        1,
        ((position.x - a.x) * dx + (position.y - a.y) * dy) / lengthSquared,
      ),
    );
    const distance = Math.hypot(
      position.x - a.x - t * dx,
      position.y - a.y - t * dy,
    );
    if (distance < bestDistance) {
      bestDistance = distance;
      heading = (Math.atan2(dy, dx) * 180) / Math.PI;
    }
  }
  return heading;
}
