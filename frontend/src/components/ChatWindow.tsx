import {
  useEffect,
  useRef,
} from "react";

import type { ChatMessage } from "../types/chat";

import Message from "./Message";
import LoadingIndicator from "./LoadingIndicator";

type WorkspaceMode =
  | "copilot"
  | "investigate";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
  mode: WorkspaceMode;
}

export default function ChatWindow({
  messages,
  loading,
  mode,
}: ChatWindowProps) {
  const endRef =
    useRef<HTMLDivElement | null>(
      null
    );

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [
    messages.length,
    loading,
  ]);

  if (
    messages.length === 0 &&
    !loading
  ) {
    return (
      <section className="welcome-panel">
        <div
          className="welcome-orb"
          aria-hidden="true"
        >
          <span />
          <span />
          <span />
        </div>

        <div className="welcome-kicker">
          {mode === "copilot"
            ? "NEXA ANALYTICS COPILOT"
            : "NEXA INVESTIGATION"}
        </div>

        <h1>
          {mode === "copilot" ? (
            <>
              Ask questions about
              <br />
              <span>
                your business.
              </span>
            </>
          ) : (
            <>
              Investigate what is
              <br />
              <span>
                driving the numbers.
              </span>
            </>
          )}
        </h1>

        <p>
          {mode === "copilot"
            ? "Explore sales, products, regions, customers, promotions and inventory using grounded business analytics."
            : "Move from a business question to a structured evidence chain across the Nexa data model."}
        </p>
      </section>
    );
  }

  return (
    <div className="chat-window">
      <div className="message-list">
        {messages.map(
          (message, index) => (
            <Message
              key={`${message.role}-${index}`}
              message={message}
            />
          )
        )}

        {loading && (
          <LoadingIndicator />
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}