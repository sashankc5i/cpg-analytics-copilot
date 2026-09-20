import {
  useState,
} from "react";

import ChatWindow from "./components/ChatWindow";

import {
  sendMessage,
} from "./services/api";

import type {
  ChatMessage,
} from "./types/chat";


function App() {

  const [
    messages,
    setMessages,
  ] = useState<ChatMessage[]>([]);

  const [
    input,
    setInput,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(null);


  const [
    conversationId,
  ] = useState(
    () =>
      `session-${Date.now()}`
  );


  async function handleSubmit(
    event: React.FormEvent
  ) {

    event.preventDefault();

    const message =
      input.trim();

    if (
      !message ||
      loading
    ) {
      return;
    }

    setError(null);

    setMessages(
      (previous) => [
        ...previous,

        {
          role: "user",
          content: message,
        },
      ]
    );

    setInput("");
    setLoading(true);


    try {

      const response =
        await sendMessage({
          message,
          conversation_id:
            conversationId,
        });


      setMessages(
        (previous) => [

          ...previous,

          {
            role: "assistant",

            content:
              response.answer,

            toolsUsed:
              response.tools_used,

            visualization:
              response.visualization,
          },

        ]
      );

    } catch (err) {

      console.error(err);

      setError(
        "Unable to connect to the analytics backend."
      );

    } finally {

      setLoading(false);

    }
  }


  function handleSuggestion(
    question: string
  ) {

    if (loading) {
      return;
    }

    setInput(question);
  }


  return (

    <div className="app">

      <header className="app-header">

        <div className="brand">

          <div className="brand-icon">
            ✦
          </div>

          <div>

            <h1>
              Nexa Analytics Copilot
            </h1>

            <p>
              CPG Business Intelligence
            </p>

          </div>

        </div>


        <div className="status">

          <span className="status-dot" />

          Analytics Online

        </div>

      </header>


      <main className="app-main">

        <ChatWindow
          messages={messages}
          loading={loading}
        />


        {messages.length === 0 && (

          <div className="quick-actions">

            {[
              "What is our total revenue?",
              "Which region performs best?",
              "What are our top products?",
              "Show me monthly revenue.",
              "Why is revenue changing?",
            ].map(
              (question) => (

                <button
                  key={question}
                  type="button"
                  onClick={() =>
                    handleSuggestion(
                      question
                    )
                  }
                >
                  {question}
                </button>

              )
            )}

          </div>

        )}


        {error && (

          <div className="error">
            {error}
          </div>

        )}


        <form
          className="input-container"
          onSubmit={handleSubmit}
        >

          <input
            value={input}

            onChange={(event) =>
              setInput(
                event.target.value
              )
            }

            placeholder="Ask a business question..."

            disabled={loading}
          />


          <button
            type="submit"

            disabled={
              loading ||
              !input.trim()
            }
          >
            →
          </button>

        </form>

      </main>

    </div>
  );
}


export default App;