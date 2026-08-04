export default function PageShell({ eyebrow, title, sub, children }) {
  return (
    <div className="main-pane">
      <header className="pane-header">
        <div className="pane-eyebrow">{eyebrow}</div>
        <h1 className="pane-title">{title}</h1>
        <p className="pane-sub">{sub}</p>
      </header>
      <div className="pane-body">{children}</div>
    </div>
  );
}
