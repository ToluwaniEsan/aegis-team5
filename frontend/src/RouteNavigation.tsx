import type { LatLon, NavView } from "./contracts/ui";
import { SeverityShape } from "./SeverityShape";
import {
  projectPoints,
  routeHeading,
  ROUTE_HEIGHT,
  ROUTE_WIDTH,
  travelledPoints,
} from "./routeGeometry";
import { useScreenStore } from "./state/store";

function formatTime(seconds: number | null): string {
  if (seconds === null) return "Unavailable";
  const total = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function BlockedNotice({
  blocked,
}: {
  blocked: NonNullable<NavView["blocked"]>;
}) {
  return (
    <div className="route-blocked">
      <SeverityShape severity="CAUTION" />
      <strong>CAUTION · ROUTE BLOCKED</strong>
      <span>
        {blocked.reason} · new ETA {formatTime(blocked.new_eta_s)}
      </span>
    </div>
  );
}

function RouteMap({ nav }: { nav: NavView }) {
  const items: LatLon[] = [
    ...nav.route,
    ...(nav.blocked?.old_route ?? []),
    ...(nav.origin ? [nav.origin] : []),
    ...(nav.destination ? [nav.destination] : []),
    ...(nav.position ? [nav.position] : []),
    ...(nav.blocked ? [nav.blocked.at] : []),
  ];
  const points = projectPoints(items);
  let index = 0;
  const route = points.slice(index, (index += nav.route.length));
  const oldRoute = points.slice(
    index,
    (index += nav.blocked?.old_route.length ?? 0),
  );
  const origin = nav.origin ? points[index++] : null;
  const destination = nav.destination ? points[index++] : null;
  const position = nav.position ? points[index++] : null;
  const blocked = nav.blocked ? points[index] : null;
  const heading = position ? routeHeading(route, position) : null;
  const line = (values: typeof points) =>
    values.map(({ x, y }) => `${x},${y}`).join(" ");
  const label = (point: { x: number; y: number }, text: string) => (
    <text
      x={point.x}
      y={point.y < 45 ? point.y + 18 : point.y - 12}
      textAnchor={point.x > ROUTE_WIDTH / 2 ? "end" : "start"}
    >
      {text}
    </text>
  );
  return (
    <svg
      className="route-map"
      viewBox={`0 0 ${ROUTE_WIDTH} ${ROUTE_HEIGHT}`}
      role="img"
      aria-label="Schematic route"
    >
      {oldRoute.length > 1 && (
        <polyline className="route-old" points={line(oldRoute)} />
      )}
      {route.length > 1 && (
        <polyline className="route-line" points={line(route)} />
      )}
      {travelledPoints(route, nav.progress_pct).length > 1 && (
        <polyline
          className="route-travelled"
          points={line(travelledPoints(route, nav.progress_pct))}
        />
      )}
      {origin && (
        <g>
          <circle className="route-origin" cx={origin.x} cy={origin.y} r="7" />
          {label(origin, nav.origin!.name)}
        </g>
      )}
      {destination && (
        <g>
          <rect
            className="route-destination"
            x={destination.x - 7}
            y={destination.y - 7}
            width="14"
            height="14"
          />
          {label(destination, nav.destination!.name)}
        </g>
      )}
      {blocked && (
        <path
          className="route-cross"
          d={`M ${blocked.x - 7} ${blocked.y - 7} l 14 14 m 0 -14 l -14 14`}
        />
      )}
      {position && heading !== null && (
        <g
          transform={`translate(${position.x} ${position.y}) rotate(${heading})`}
        >
          <path className="route-vehicle" d="M 6 0 L -4 -5 L -4 5 Z" />
        </g>
      )}
    </svg>
  );
}

export function RouteNavigation() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const nav = snapshot?.nav;
  const observed = Boolean(nav?.updated_at);
  const stale = disconnected || !observed || Boolean(nav?.stale);
  const age = nav?.age_s == null ? null : `${nav.age_s.toFixed(0)} s`;
  return (
    <section className="navigation" aria-label="Navigation details">
      <header className="navigation-header">
        <h2>Route &amp; navigation</h2>
        <span>
          {stale
            ? `OUT OF DATE${age ? ` · ${age}` : ""}`
            : age
              ? `updated ${age} ago`
              : "age unavailable"}
        </span>
      </header>
      <div className={stale ? "navigation-stale" : undefined}>
        {!snapshot ? (
          <div className="route-placeholder">Awaiting navigation status</div>
        ) : !snapshot.mission.active ? (
          <>
            {observed && nav?.blocked ? (
              <>
                <div>No active mission</div>
                <RouteMap nav={nav} />
                <BlockedNotice blocked={nav.blocked} />
              </>
            ) : (
              <div className="route-placeholder">No active mission</div>
            )}
          </>
        ) : !observed || !nav ? (
          <div className="route-placeholder">Awaiting navigation status</div>
        ) : (
          <>
            {nav.route.length ||
            nav.origin ||
            nav.destination ||
            nav.position ||
            nav.blocked ? (
              <RouteMap nav={nav} />
            ) : (
              <div className="route-placeholder">Route unavailable</div>
            )}
            {nav.blocked && <BlockedNotice blocked={nav.blocked} />}
            <div className="route-progress">
              <div>
                <strong>ROUTE PROGRESS</strong>
                <span>
                  {nav.progress_pct === null
                    ? "Unavailable"
                    : `${nav.progress_pct} %`}
                </span>
              </div>
              <div className="route-progress-track">
                {nav.progress_pct !== null && (
                  <div
                    style={{
                      width: `${Math.max(0, Math.min(100, nav.progress_pct))}%`,
                    }}
                  />
                )}
              </div>
            </div>
            <div className="navigation-values">
              <div>
                <span>ETA</span>
                <strong>{formatTime(nav.eta_s)}</strong>
              </div>
              <div>
                <span>MOTION</span>
                <strong>{nav.moving ? "Moving" : "Stopped"}</strong>
                <small>
                  {nav.speed_mps === null
                    ? "Speed unavailable"
                    : `${nav.speed_mps.toFixed(1)} m/s`}
                </small>
              </div>
              <div>
                <span>POSITION</span>
                <small>
                  {nav.position
                    ? `${nav.position.lat.toFixed(4)}, ${nav.position.lon.toFixed(4)}`
                    : "Unavailable"}
                </small>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
