import type { ChatMessage } from "../types/chat";
import Message from "./Message";
import LoadingIndicator from "./LoadingIndicator";

type WorkspaceMode = "copilot" | "investigate";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
  mode: WorkspaceMode;
}

export default function ChatWindow({ messages, loading, mode }: ChatWindowProps) {
  return (
    <div className="chat-window">
      {messages.length === 0 && !loading && (
        <div className="welcome-panel">
          <div className="welcome-kicker">
            <span className="kicker-mark" />
            {mode === "copilot" ? "BUSINESS INTELLIGENCE" : "INVESTIGATION WORKSPACE"}
          </div>

          <h1>
            {mode === "copilot" ? (
              <>Understand the business<br /><span>behind the numbers.</span></>
            ) : (
              <>Turn a business question<br /><span>into an investigation.</span></>
            )}
          </h1>

          <p>
            {mode === "copilot"
              ? "Ask about sales, products, regions, customers, promotions and inventory. Nexa translates natural language into grounded analytics."
              : "Trace a business problem across multiple dimensions, collect evidence and build toward an evidence-backed finding."}
          </p>

          <div className="capability-row">
            <div className="capability-card">
              <span className="capability-index">01</span>
              <strong>Sales</strong>
              <span>Revenue & trends</span>
            </div>
            <div className="capability-card">
              <span className="capability-index">02</span>
              <strong>Products</strong>
              <span>Performance & mix</span>
            </div>
            <div className="capability-card">
              <span className="capability-index">03</span>
              <strong>Regions</strong>
              <span>Market performance</span>
            </div>
            <div className={`capability-card ${mode === "investigate" ? "accent" : ""}`}>
              <span className="capability-index">04</span>
              <strong>Investigate</strong>
              <span>Drivers & evidence</span>
            </div>
          </div>
        </div>
      )}

      {messages.map((message, index) => (
        <Message key={`${message.role}-${index}`} message={message} />
      ))}

      {loading && <LoadingIndicator />}
    </div>
  );
}
