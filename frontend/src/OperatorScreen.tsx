export function OperatorScreen() {
  return (
    <>
      <main id="app" aria-label="Operator Screen">
        <header className="top" aria-label="Top bar" />
        <section className="panel" aria-label="Payload and vehicle health" />
        <section className="panel" aria-label="Route and navigation" />
        <section className="panel panel-right" aria-label="Mission controls" />
        <footer className="bottom" aria-label="Alerts and delivery" />
      </main>
      <p className="window-warning">Increase the window size to at least 1366 × 768.</p>
    </>
  );
}
