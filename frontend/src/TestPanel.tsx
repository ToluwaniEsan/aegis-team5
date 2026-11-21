import { useRef, useState } from "react";
import { EStopButton } from "./EStopButton";
import { useScreenStore } from "./state/store";

type Field = {
  name: string;
  label: string;
  kind: "number" | "text" | "choice" | "boolean";
  choices?: string[];
};
type Action = {
  target: string;
  action: string;
  label: string;
  fields: Field[];
};
const health = ["OK", "WARN", "FAULT"];
const actions: Action[] = [
  {
    target: "payload",
    action: "shift",
    label: "Inject shift",
    fields: [{ name: "cm", label: "Shift (cm)", kind: "number" }],
  },
  {
    target: "payload",
    action: "sensor",
    label: "Set sensor",
    fields: [
      {
        name: "sensor",
        label: "Sensor",
        kind: "choice",
        choices: ["load_cell", "lock", "shift"],
      },
      {
        name: "health",
        label: "Sensor health",
        kind: "choice",
        choices: health,
      },
    ],
  },
  {
    target: "payload",
    action: "mass_override",
    label: "Override mass",
    fields: [{ name: "kg", label: "Mass (kg)", kind: "number" }],
  },
  {
    target: "payload",
    action: "release_jam",
    label: "Set release jam",
    fields: [{ name: "on", label: "Release jam", kind: "boolean" }],
  },
  {
    target: "payload",
    action: "controller_crash",
    label: "Stop controller",
    fields: [],
  },
  { target: "payload", action: "unload", label: "Unload payload", fields: [] },
  {
    target: "link",
    action: "set",
    label: "Set link",
    fields: [
      { name: "latency_ms", label: "Latency (ms)", kind: "number" },
      { name: "loss_pct", label: "Loss (%)", kind: "number" },
    ],
  },
  {
    target: "link",
    action: "outage",
    label: "Start outage",
    fields: [{ name: "seconds", label: "Outage (s)", kind: "number" }],
  },
  { target: "nav", action: "depart", label: "Depart", fields: [] },
  { target: "nav", action: "arrive", label: "Arrive", fields: [] },
  { target: "nav", action: "stop", label: "Stop navigation", fields: [] },
  {
    target: "nav",
    action: "block_route",
    label: "Block route",
    fields: [{ name: "reason", label: "Reason", kind: "text" }],
  },
  {
    target: "nav",
    action: "health",
    label: "Set navigation health",
    fields: [
      {
        name: "health",
        label: "Navigation health",
        kind: "choice",
        choices: health,
      },
    ],
  },
  {
    target: "power",
    action: "battery",
    label: "Set battery",
    fields: [{ name: "pct", label: "Battery (%)", kind: "number" }],
  },
  {
    target: "power",
    action: "drivetrain",
    label: "Set drivetrain",
    fields: [
      {
        name: "health",
        label: "Drivetrain health",
        kind: "choice",
        choices: health,
      },
    ],
  },
  {
    target: "team1",
    action: "mode",
    label: "Set Team 1 mode",
    fields: [{ name: "mode", label: "Team 1 mode", kind: "text" }],
  },
];

function InjectForm({
  action,
  onResult,
}: {
  action: Action;
  onResult: (text: string) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      action.fields.map((field) => [
        field.name,
        field.kind === "boolean" ? "false" : (field.choices?.[0] ?? ""),
      ]),
    ),
  );
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  const available = useScreenStore(
    (state) =>
      state.snapshot?.test_mode === true &&
      state.connection === "connected" &&
      !state.screenDisconnected,
  );
  async function submit() {
    const state = useScreenStore.getState();
    if (
      busy.current ||
      state.snapshot?.test_mode !== true ||
      state.connection !== "connected" ||
      state.screenDisconnected
    )
      return;
    const params: Record<string, unknown> = {};
    for (const field of action.fields) {
      const value = values[field.name];
      if (
        !value.trim() ||
        (field.kind === "number" && !Number.isFinite(Number(value)))
      ) {
        onResult(
          `${action.label}: ${field.label} is required and must be valid`,
        );
        return;
      }
      params[field.name] =
        field.kind === "number"
          ? Number(value)
          : field.kind === "boolean"
            ? value === "true"
            : value;
    }
    busy.current = true;
    setPending(true);
    try {
      const response = await fetch("/api/test/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: action.target,
          action: action.action,
          params,
        }),
      });
      const body: unknown = await response.json();
      if (!response.ok) {
        const reason =
          body && typeof body === "object" && "detail" in body
            ? String(body.detail)
            : `HTTP ${response.status}`;
        onResult(`${action.label}: ${reason}`);
      } else {
        const id =
          body && typeof body === "object" && "msg_id" in body
            ? String(body.msg_id)
            : "Unavailable";
        onResult(`${action.label}: sent · ${id}`);
      }
    } catch {
      onResult(
        `${action.label}: result unavailable; the injection may have been sent`,
      );
    } finally {
      busy.current = false;
      setPending(false);
    }
  }
  return (
    <form
      className="inject-form"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {action.fields.map((field) => (
        <label key={field.name}>
          {field.label}
          {field.kind === "choice" || field.kind === "boolean" ? (
            <select
              value={values[field.name]}
              onChange={(event) =>
                setValues({ ...values, [field.name]: event.target.value })
              }
            >
              {(field.kind === "boolean"
                ? ["false", "true"]
                : (field.choices ?? [])
              ).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={field.kind}
              value={values[field.name]}
              onChange={(event) =>
                setValues({ ...values, [field.name]: event.target.value })
              }
            />
          )}
        </label>
      ))}
      <button type="submit" disabled={!available || pending}>
        {action.label}
      </button>
    </form>
  );
}

export function TestPanel() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const connected = useScreenStore(
    (state) => state.connection === "connected" && !state.screenDisconnected,
  );
  const [results, setResults] = useState<string[]>([]);
  return (
    <main className="test-panel">
      <header>
        <h1>Test injection</h1>
        <EStopButton active={snapshot?.estop_active === true} />
      </header>
      {!snapshot ? (
        <p>Awaiting ground station data</p>
      ) : !snapshot.test_mode ? (
        <p>Test mode is unavailable</p>
      ) : (
        <>
          {!connected && (
            <p role="alert">
              Screen disconnected from ground station. Injections unavailable.
            </p>
          )}
          {(["payload", "link", "nav", "power", "team1"] as const).map(
            (target) => (
              <section key={target}>
                <h2>{target.toUpperCase()}</h2>
                {actions
                  .filter((action) => action.target === target)
                  .map((action) => (
                    <InjectForm
                      key={action.action}
                      action={action}
                      onResult={(text) =>
                        setResults((old) => [text, ...old].slice(0, 10))
                      }
                    />
                  ))}
              </section>
            ),
          )}
          <section>
            <h2>LAST 10 RESULTS</h2>
            <ol>
              {results.map((result, index) => (
                <li key={`${index}-${result}`}>{result}</li>
              ))}
            </ol>
          </section>
        </>
      )}
    </main>
  );
}
