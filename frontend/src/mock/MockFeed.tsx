import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Snapshot } from "../contracts/ui";
import { fixtureNames, startMockFeed } from "../net/mock";
import type { FixtureName } from "../net/mock";
import { useScreenStore } from "../state/store";

const SnapshotContext = createContext<Snapshot | null>(null);

export function useMockSnapshot() {
  return useContext(SnapshotContext);
}

export function MockFeed({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [name, setName] = useState<FixtureName>("idle");
  const [feed, setFeed] = useState<ReturnType<typeof startMockFeed> | null>(
    null,
  );
  useEffect(() => {
    useScreenStore.getState().setConnection("connected");
    useScreenStore.getState().setScreenDisconnected(false);
    const running = startMockFeed((next, fixtureName) => {
      useScreenStore.getState().setSnapshot(next);
      setSnapshot(next);
      setName(fixtureName);
    });
    setFeed(running);
    return () => {
      running.stop();
      useScreenStore.getState().setConnection("disconnected");
    };
  }, []);
  return (
    <SnapshotContext.Provider value={snapshot}>
      {children}
      {import.meta.env.DEV && (
        <label className="fixture-picker">
          Fixture
          <select
            value={name}
            onChange={(event) => {
              const selected = fixtureNames.find(
                (item) => item === event.target.value,
              );
              if (selected) feed?.select(selected);
            }}
          >
            {fixtureNames.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      )}
    </SnapshotContext.Provider>
  );
}
