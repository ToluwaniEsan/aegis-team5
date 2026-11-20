import { useScreenStore } from "./state/store";

export function DeliverySummary() {
  const delivery = useScreenStore((state) => state.snapshot?.delivery);
  return (
    <div className={`delivery-summary${delivery ? " delivery-confirmed" : ""}`}>
      {delivery ? (
        <>
          <strong>✓ DELIVERED · CONFIRMED</strong>
          <dl>
            <div>
              <dt>Payload</dt>
              <dd>{delivery.payload_id}</dd>
            </div>
            <div>
              <dt>Destination</dt>
              <dd>{delivery.destination.name}</dd>
            </div>
            <div>
              <dt>Released</dt>
              <dd>{delivery.released_at.slice(11, 19)}Z</dd>
            </div>
            <div>
              <dt>Confirmed in</dt>
              <dd>{delivery.confirm_latency_s.toFixed(1)} s</dd>
            </div>
            <div>
              <dt>Mass · energy</dt>
              <dd>
                {delivery.mass_kg.toFixed(1)} kg ·{" "}
                {delivery.energy_used_wh.toFixed(1)} Wh
              </dd>
            </div>
          </dl>
        </>
      ) : (
        <span>Delivery unavailable</span>
      )}
    </div>
  );
}
