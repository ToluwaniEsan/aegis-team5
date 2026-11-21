import { useEffect } from "react";
import type { ReactNode } from "react";
import { MockFeed } from "../mock/MockFeed";
import { socketClient } from "./socket";

export function DataSource({
  children,
  mock,
}: {
  children: ReactNode;
  mock: boolean;
}) {
  useEffect(() => {
    if (mock) return;
    socketClient.start();
    return () => socketClient.stop();
  }, [mock]);
  return mock ? <MockFeed>{children}</MockFeed> : children;
}
