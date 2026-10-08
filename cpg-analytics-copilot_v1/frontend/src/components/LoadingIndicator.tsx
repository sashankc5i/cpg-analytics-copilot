export default function LoadingIndicator() {
  return (
    <div className="message-row message-row-assistant">
      <div className="assistant-avatar" aria-hidden="true">
        <span className="mini-shape mini-one" />
        <span className="mini-shape mini-two" />
      </div>
      <div className="message-bubble message-assistant loading-card">
        <div className="message-meta">
          <span className="message-role">NEXA INTELLIGENCE</span>
          <span className="message-type">WORKING</span>
        </div>
        <div className="loading">
          <span /><span /><span />
          <span className="loading-text">Analyzing your business question…</span>
        </div>
      </div>
    </div>
  );
}
