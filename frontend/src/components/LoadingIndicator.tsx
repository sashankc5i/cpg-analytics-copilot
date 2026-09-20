export default function LoadingIndicator() {
  return (
    <div className="message-row message-row-assistant">

      <div className="message-bubble message-assistant">

        <div className="message-role">
          Nexa Copilot
        </div>

        <div className="loading">
          <span />
          <span />
          <span />
          <span className="loading-text">
            Analyzing...
          </span>
        </div>

      </div>

    </div>
  );
}