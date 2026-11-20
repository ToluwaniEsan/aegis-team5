import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "./styles/tokens.css";
import "./styles/base.css";
import { OperatorScreen } from "./OperatorScreen";
import { DataSource } from "./net/DataSource";
import { TestPanel } from "./TestPanel";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <DataSource mock={import.meta.env.VITE_MOCK === "1"}>
      {window.location.pathname === "/test" ? (
        <TestPanel />
      ) : (
        <OperatorScreen />
      )}
    </DataSource>
  </React.StrictMode>,
);
