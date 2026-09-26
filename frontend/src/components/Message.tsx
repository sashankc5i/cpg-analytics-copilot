import ReactMarkdown from "react-markdown";

import type { ChatMessage } from "../types/chat";
import ChartRenderer from "./ChartRenderer";

interface MessageProps {
  message: ChatMessage;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === "user";

  return (
    <article
      className={`message-row ${
        isUser ? "message-row-user" : "message-row-assistant"
      }`}
    >
      {!isUser && (
        <div className="assistant-avatar" aria-hidden="true">
          <span className="mini-shape mini-one" />
          <span className="mini-shape mini-two" />
        </div>
      )}

      <div
        className={`message-bubble ${
          isUser ? "message-user" : "message-assistant"
        }`}
      >
        {!isUser && (
          <div className="message-meta">
            <span className="message-role">NEXA</span>
          </div>
        )}

        <div className="message-content">
          <ReactMarkdown
            components={{
              p: ({ children }) => (
                <p className="markdown-paragraph">{children}</p>
              ),

              strong: ({ children }) => (
                <strong className="markdown-bold">{children}</strong>
              ),

              ul: ({ children }) => (
                <ul className="markdown-list">{children}</ul>
              ),

              ol: ({ children }) => (
                <ol className="markdown-list">{children}</ol>
              ),

              li: ({ children }) => (
                <li className="markdown-list-item">{children}</li>
              ),

              h1: ({ children }) => (
                <h1 className="markdown-heading">{children}</h1>
              ),

              h2: ({ children }) => (
                <h2 className="markdown-heading">{children}</h2>
              ),

              h3: ({ children }) => (
                <h3 className="markdown-heading">{children}</h3>
              ),

              code: ({ children }) => (
                <code className="markdown-code">{children}</code>
              ),

              blockquote: ({ children }) => (
                <blockquote className="markdown-quote">
                  {children}
                </blockquote>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {!isUser &&
          message.toolsUsed &&
          message.toolsUsed.length > 0 && (
            <details className="evidence-section">
              <summary>Sources</summary>

              <div className="tool-list">
                {message.toolsUsed.map((tool) => (
                  <span className="tool-badge" key={tool}>
                    {tool}
                  </span>
                ))}
              </div>
            </details>
          )}

        {!isUser && message.visualization && (
          <ChartRenderer visualization={message.visualization} />
        )}
      </div>
    </article>
  );
}