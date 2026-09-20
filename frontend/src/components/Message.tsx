import type {
  ChatMessage,
} from "../types/chat";

import ChartRenderer from "./ChartRenderer";


interface MessageProps {
  message: ChatMessage;
}


export default function Message({
  message,
}: MessageProps) {

  const isUser =
    message.role === "user";


  return (
    <div
      className={`message-row ${
        isUser
          ? "message-row-user"
          : "message-row-assistant"
      }`}
    >

      <div
        className={`message-bubble ${
          isUser
            ? "message-user"
            : "message-assistant"
        }`}
      >

        <div className="message-role">

          {isUser
            ? "You"
            : "Nexa Copilot"}

        </div>


        <div className="message-content">

          {message.content}

        </div>


        {!isUser &&
          message.toolsUsed &&
          message.toolsUsed.length > 0 && (

            <div className="tools-used">

              <span className="tools-label">
                Analysis:
              </span>

              {message.toolsUsed.map(
                (tool) => (

                  <span
                    className="tool-badge"
                    key={tool}
                  >
                    {tool}
                  </span>

                )
              )}

            </div>

          )}


        {!isUser &&
          message.visualization && (

            <ChartRenderer
              visualization={
                message.visualization
              }
            />

          )}

      </div>

    </div>
  );
}