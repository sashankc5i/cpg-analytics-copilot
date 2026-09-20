import type {
  ChatMessage,
} from "../types/chat";

import Message from "./Message";
import LoadingIndicator from "./LoadingIndicator";


interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
}


export default function ChatWindow({
  messages,
  loading,
}: ChatWindowProps) {

  return (
    <div className="chat-window">

      {messages.length === 0 && !loading && (

        <div className="welcome">

          <div className="welcome-icon">
            ✦
          </div>

          <h2>
            Ask your business data anything.
          </h2>

          <p>
            Analyze sales, products, regions,
            customers, promotions, and inventory
            using natural language.
          </p>

          <div className="suggestions">

            <div className="suggestion">
              What is our total revenue?
            </div>

            <div className="suggestion">
              Which region performs best?
            </div>

            <div className="suggestion">
              What are our top products?
            </div>

            <div className="suggestion">
              Why is revenue changing?
            </div>

          </div>

        </div>
      )}

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

    </div>
  );
}