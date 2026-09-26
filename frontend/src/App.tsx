import { useState } from "react";

import ChatWindow from "./components/ChatWindow";
import {
  sendMessage,
  streamChallenge,
  streamInvestigation,
  type ChallengeStreamEvent,
  type InvestigationStreamEvent,
} from "./services/api";

import type { ChatMessage } from "./types/chat";


type WorkspaceMode =
  | "copilot"
  | "investigate";


function BrandMark() {
  return (
    <div
      className="brand-mark"
      aria-hidden="true"
    >
      <span className="brand-shape brand-shape-one" />
      <span className="brand-shape brand-shape-two" />
      <span className="brand-shape brand-shape-three" />
    </div>
  );
}


function SidebarIcon({
  type,
}: {
  type:
    | "chat"
    | "investigate"
    | "chart"
    | "product"
    | "customer"
    | "inventory";
}) {

  const paths = {

    chat: (
      <>
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v7a2.5 2.5 0 0 1-2.5 2.5H11l-4.5 3v-3H6.5A2.5 2.5 0 0 1 4 12.5z" />
        <path d="M8 8h8M8 11h5" />
      </>
    ),

    investigate: (
      <>
        <circle
          cx="10.5"
          cy="10.5"
          r="5.5"
        />

        <path d="m15 15 5 5M8.5 10.5h4M10.5 8.5v4" />
      </>
    ),

    chart: (
      <>
        <path d="M5 19V9M12 19V5M19 19v-7" />
        <path d="M3 19h18" />
      </>
    ),

    product: (
      <>
        <path d="m12 3 7 4v10l-7 4-7-4V7z" />
        <path d="m5 7 7 4 7-4M12 11v10" />
      </>
    ),

    customer: (
      <>
        <circle
          cx="12"
          cy="8"
          r="3"
        />

        <path d="M5 20a7 7 0 0 1 14 0" />
      </>
    ),

    inventory: (
      <>
        <path d="M4 7h16v13H4z" />
        <path d="M8 7V5h8v2M8 11h8M8 15h5" />
      </>
    ),
  };


  return (
    <svg
      viewBox="0 0 24 24"
      className="sidebar-icon"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[type]}
    </svg>
  );
}


function App() {

  /*
   * ------------------------------------------------
   * WORKSPACE MESSAGE STATE
   * ------------------------------------------------
   *
   * Copilot and Investigation intentionally have
   * separate message histories.
   *
   * Challenge reports belong to the Investigation
   * workspace because they challenge an existing
   * investigation conclusion.
   */

  const [
    copilotMessages,
    setCopilotMessages,
  ] = useState<ChatMessage[]>([]);


  const [
    investigationMessages,
    setInvestigationMessages,
  ] = useState<ChatMessage[]>([]);


  /*
   * ------------------------------------------------
   * WORKSPACE SESSION IDs
   * ------------------------------------------------
   */

  const [
    copilotConversationId,
  ] = useState(
    () => `copilot-${Date.now()}`
  );


  const [
    investigationConversationId,
  ] = useState(
    () => `investigation-${Date.now()}`
  );


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
    mode,
    setMode,
  ] = useState<WorkspaceMode>(
    "copilot"
  );


  /*
   * ------------------------------------------------
   * VISIBLE MESSAGE COLLECTION
   * ------------------------------------------------
   */

  const messages =
    mode === "copilot"
      ? copilotMessages
      : investigationMessages;


  /*
   * ------------------------------------------------
   * INVESTIGATION STATE
   * ------------------------------------------------
   *
   * Challenge Mode is only available after the
   * Investigation workspace has produced an answer.
   */

  const investigationHasConclusion =
    investigationMessages.some(
      (message) =>
        message.role === "assistant" &&
        message.content.trim().length > 0
    );


  /*
   * ------------------------------------------------
   * COPILOT MESSAGE HELPERS
   * ------------------------------------------------
   */

  function addCopilotMessage(
    message: ChatMessage
  ) {

    setCopilotMessages(
      (previous) => [
        ...previous,
        message,
      ]
    );
  }


  /*
   * ------------------------------------------------
   * INVESTIGATION MESSAGE HELPERS
   * ------------------------------------------------
   */

  function addInvestigationMessage(
    message: ChatMessage
  ) {

    setInvestigationMessages(
      (previous) => [
        ...previous,
        message,
      ]
    );
  }


  /*
   * ------------------------------------------------
   * SUBMIT
   * ------------------------------------------------
   */

  async function handleSubmit(
    event: React.FormEvent
  ) {

    event.preventDefault();


    const message =
      input.trim();


    if (!message || loading) {
      return;
    }


    setError(null);


    /*
     * Add the user's message to the
     * CURRENT workspace only.
     */

    if (mode === "copilot") {

      addCopilotMessage({
        role: "user",
        content: message,
      });

    } else {

      addInvestigationMessage({
        role: "user",
        content: message,
      });
    }


    setInput("");
    setLoading(true);


    /*
     * ================================================
     * COPILOT
     * ================================================
     */

    if (mode === "copilot") {

      try {

        const response =
          await sendMessage({
            message,
            conversation_id:
              copilotConversationId,
          });


        addCopilotMessage({
          role: "assistant",
          content: response.answer,
          toolsUsed:
            response.tools_used,
          visualization:
            response.visualization,
        });

      } catch (err) {

        console.error(err);

        setError(
          "Unable to connect to the analytics backend. Check that the API is running."
        );

      } finally {

        setLoading(false);
      }


      return;
    }


    /*
     * ================================================
     * INVESTIGATION
     * ================================================
     */

    let assistantMessageCreated =
      false;


    try {

      await streamInvestigation(
        {
          message,
          conversation_id:
            investigationConversationId,
        },

        (
          event: InvestigationStreamEvent
        ) => {

          handleInvestigationEvent(
            event,
            assistantMessageCreated,
            () => {
              assistantMessageCreated =
                true;
            }
          );
        }
      );

    } catch (err) {

      console.error(err);

      setError(
        "Unable to complete the investigation. Check that the API is running."
      );

    } finally {

      setLoading(false);
    }
  }


  /*
   * ------------------------------------------------
   * INVESTIGATION STREAM EVENTS
   * ------------------------------------------------
   */

  function handleInvestigationEvent(
    event: InvestigationStreamEvent,
    assistantMessageCreated: boolean,
    markAssistantCreated: () => void
  ) {

    if (
      event.type ===
      "investigation_started"
    ) {
      return;
    }


    /*
     * The investigation plan is internal workflow
     * information.
     *
     * Hypotheses are also currently kept out of the
     * normal chat stream because the final synthesis
     * already incorporates them.
     */

    if (
      event.type === "plan" ||
      event.type === "hypotheses"
    ) {
      return;
    }


    /*
     * Create an empty assistant message when
     * synthesis begins.
     */

    if (
      event.type ===
      "answer_start"
    ) {

      if (
        !assistantMessageCreated
      ) {

        addInvestigationMessage({
          role: "assistant",
          content: "",
          messageType: "normal",
        });


        markAssistantCreated();
      }


      return;
    }


    /*
     * Append every streamed token to the
     * Investigation assistant message.
     */

    if (
      event.type === "token"
    ) {

      const token =
        typeof event.data ===
        "string"
          ? event.data
          : "";


      if (!token) {
        return;
      }


      /*
       * Safety fallback if a token arrives
       * before answer_start.
       */

      if (
        !assistantMessageCreated
      ) {

        addInvestigationMessage({
          role: "assistant",
          content: token,
          messageType: "normal",
        });


        markAssistantCreated();

        return;
      }


      setInvestigationMessages(
        (previous) => {

          if (
            previous.length === 0
          ) {
            return previous;
          }


          const updated = [
            ...previous,
          ];


          const lastIndex =
            updated.length - 1;


          const lastMessage =
            updated[lastIndex];


          /*
           * Only append to the assistant
           * message.
           */

          if (
            lastMessage.role !==
            "assistant"
          ) {

            updated.push({
              role: "assistant",
              content: token,
              messageType: "normal",
            });


            return updated;
          }


          updated[lastIndex] = {
            ...lastMessage,
            content:
              lastMessage.content +
              token,
          };


          return updated;
        }
      );


      return;
    }


    if (
      event.type ===
      "answer_end"
    ) {
      return;
    }


    if (
      event.type ===
      "error"
    ) {

      const errorMessage =
        typeof event.data ===
        "string"
          ? event.data
          : "Investigation failed.";


      setError(
        errorMessage
      );
    }
  }


  /*
   * ------------------------------------------------
   * CHALLENGE MY CONCLUSION
   * ------------------------------------------------
   */

  async function handleChallenge() {

    if (
      loading ||
      !investigationHasConclusion
    ) {
      return;
    }


    setError(null);
    setLoading(true);


    let challengeMessageCreated =
      false;


    try {

      await streamChallenge(
        {
          /*
           * The backend does NOT use this as the
           * original conclusion.
           *
           * It retrieves the latest investigation
           * from the server-side session manager.
           */
          message:
            "Challenge my conclusion",

          conversation_id:
            investigationConversationId,
        },

        (
          event: ChallengeStreamEvent
        ) => {

          handleChallengeEvent(
            event,
            challengeMessageCreated,
            () => {
              challengeMessageCreated =
                true;
            }
          );
        }
      );

    } catch (err) {

      console.error(err);

      setError(
        "Unable to challenge the investigation conclusion. Check that the API is running."
      );

    } finally {

      setLoading(false);
    }
  }


  /*
   * ------------------------------------------------
   * CHALLENGE STREAM EVENTS
   * ------------------------------------------------
   */

  function handleChallengeEvent(
    event: ChallengeStreamEvent,
    challengeMessageCreated: boolean,
    markChallengeCreated: () => void
  ) {

    /*
     * These events represent internal challenge
     * workflow information.
     *
     * We currently keep them out of the chat and
     * display the final streamed challenge report.
     */

    if (
      event.type ===
        "challenge_started" ||
      event.type ===
        "claims" ||
      event.type ===
        "challenge_plan" ||
      event.type ===
        "challenge_evidence"
    ) {
      return;
    }


    /*
     * Start a NEW assistant message.
     *
     * This is important:
     *
     * We must NOT append the challenge response
     * to the previous investigation conclusion.
     */

    if (
      event.type ===
      "answer_start"
    ) {

      if (
        !challengeMessageCreated
      ) {

        addInvestigationMessage({
          role: "assistant",
          content: "",
          messageType: "challenge",
        });


        markChallengeCreated();
      }


      return;
    }


    /*
     * Append streamed challenge tokens.
     */

    if (
      event.type === "token"
    ) {

      const token =
        typeof event.data ===
        "string"
          ? event.data
          : "";


      if (!token) {
        return;
      }


      /*
       * Safety fallback.
       */

      if (
        !challengeMessageCreated
      ) {

        addInvestigationMessage({
          role: "assistant",
          content: token,
          messageType: "challenge",
        });


        markChallengeCreated();

        return;
      }


      setInvestigationMessages(
        (previous) => {

          if (
            previous.length === 0
          ) {
            return previous;
          }


          const updated = [
            ...previous,
          ];


          const lastIndex =
            updated.length - 1;


          const lastMessage =
            updated[lastIndex];


          /*
           * Challenge synthesis should always
           * append to its own assistant message.
           */

          if (
            lastMessage.role !==
            "assistant"
          ) {

            updated.push({
              role: "assistant",
              content: token,
              messageType: "challenge",
            });


            return updated;
          }


          updated[lastIndex] = {
            ...lastMessage,
            content:
              lastMessage.content +
              token,
            messageType:
              "challenge",
          };


          return updated;
        }
      );


      return;
    }


    if (
      event.type ===
      "answer_end"
    ) {
      return;
    }


    if (
      event.type ===
      "error"
    ) {

      const errorMessage =
        typeof event.data ===
        "string"
          ? event.data
          : "Challenge analysis failed.";


      setError(
        errorMessage
      );
    }
  }


  /*
   * ------------------------------------------------
   * QUICK QUESTIONS
   * ------------------------------------------------
   */

  function handleSuggestion(
    question: string
  ) {

    if (loading) {
      return;
    }


    setInput(question);
  }


  const quickQuestions =
    mode === "investigate"
      ? [
          "Why is revenue changing?",
          "What is driving our sales performance?",
          "Find the biggest business issue in the data",
        ]
      : [
          "What is our total revenue?",
          "Which region performs best?",
          "What are our top products?",
          "Show me monthly revenue.",
        ];


  /*
   * ------------------------------------------------
   * UI
   * ------------------------------------------------
   */

  return (
    <div className="app-shell">

      <aside className="sidebar">

        <div className="sidebar-brand">

          <BrandMark />

          <div>

            <div className="sidebar-brand-name">
              Nexa
            </div>

            <div className="sidebar-brand-subtitle">
              INTELLIGENCE
            </div>

          </div>

        </div>


        <div className="sidebar-section-label">
          WORKSPACE
        </div>


        <nav
          className="sidebar-nav"
          aria-label="Workspace"
        >

          <button
            className={`nav-item ${
              mode === "copilot"
                ? "active"
                : ""
            }`}
            type="button"
            onClick={() =>
              setMode("copilot")
            }
            disabled={loading}
          >

            <SidebarIcon type="chat" />

            <span>
              Copilot
            </span>

          </button>


          <button
            className={`nav-item ${
              mode === "investigate"
                ? "active"
                : ""
            }`}
            type="button"
            onClick={() =>
              setMode("investigate")
            }
            disabled={loading}
          >

            <SidebarIcon
              type="investigate"
            />

            <span>
              Investigate
            </span>

          </button>

        </nav>


        <div className="sidebar-section-label">
          ANALYTICS
        </div>


        <nav
          className="sidebar-nav"
          aria-label="Analytics"
        >

          <button
            className="nav-item muted"
            type="button"
          >

            <SidebarIcon type="chart" />

            <span>
              Sales
            </span>

          </button>


          <button
            className="nav-item muted"
            type="button"
          >

            <SidebarIcon type="product" />

            <span>
              Products
            </span>

          </button>


          <button
            className="nav-item muted"
            type="button"
          >

            <SidebarIcon type="customer" />

            <span>
              Customers
            </span>

          </button>


          <button
            className="nav-item muted"
            type="button"
          >

            <SidebarIcon type="inventory" />

            <span>
              Inventory
            </span>

          </button>

        </nav>


        <div className="sidebar-bottom">

          <div className="data-status">

            <span className="status-dot" />

            <div>

              <strong>
                Analytics online
              </strong>

              <span>
                Nexa CPG data connected
              </span>

            </div>

          </div>


          <div className="sidebar-footer">
            Human · AI · Impact
          </div>

        </div>

      </aside>


      <section className="workspace">

        <header className="topbar">

          <div className="topbar-context">

            <span className="eyebrow">
              CPG BUSINESS INTELLIGENCE
            </span>

            <span className="context-divider" />

            <span className="context-name">
              Nexa Analytics Copilot
            </span>

          </div>


          <div className="topbar-status">

            <span className="status-dot" />

            Analytics Online

          </div>

        </header>


        <main className="workspace-main">

          <div className="workspace-content">

            <ChatWindow
              messages={messages}
              loading={loading}
              mode={mode}
            />


            {/*
             * ------------------------------------------------
             * CHALLENGE ACTION
             * ------------------------------------------------
             *
             * Only available in Investigation Mode after
             * an investigation has produced a conclusion.
             */}

            {mode === "investigate" &&
              investigationHasConclusion && (
                <section className="challenge-area">

                  <button
                    type="button"
                    className="challenge-button"
                    onClick={
                      handleChallenge
                    }
                    disabled={loading}
                  >

                    <span>
                      {loading
                        ? "Challenging conclusion..."
                        : "Challenge My Conclusion"}
                    </span>

                    <span>
                      →
                    </span>

                  </button>

                  <p className="challenge-note">
                    Test the conclusion against
                    supporting, contradictory, and
                    missing evidence.
                  </p>

                </section>
              )}


            {messages.length === 0 && (
              <section className="quick-area">

                <div className="quick-heading">

                  <span>
                    START WITH A QUESTION
                  </span>

                  <span className="quick-heading-line" />

                </div>


                <div className="quick-actions">

                  {quickQuestions.map(
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

                        <span>
                          {question}
                        </span>

                        <span className="quick-arrow">
                          →
                        </span>

                      </button>

                    )
                  )}

                </div>

              </section>
            )}


            {error && (
              <div className="error">
                {error}
              </div>
            )}


            <form
              className="composer"
              onSubmit={handleSubmit}
            >

              <div className="composer-mode">

                <span
                  className={`mode-dot ${mode}`}
                />

                {mode === "copilot"
                  ? "Copilot"
                  : "Investigation"}

              </div>


              <input
                value={input}
                onChange={(event) =>
                  setInput(
                    event.target.value
                  )
                }
                placeholder={
                  mode === "copilot"
                    ? "Ask Nexa about your business..."
                    : "Describe the business problem you want to investigate..."
                }
                disabled={loading}
                aria-label="Business question"
              />


              <button
                type="submit"
                disabled={
                  loading ||
                  !input.trim()
                }
                aria-label="Send question"
              >

                <span>
                  →
                </span>

              </button>

            </form>


            <p className="composer-note">
              Nexa uses approved analytics tools
              and available business data to ground
              its responses.
            </p>

          </div>

        </main>

      </section>

    </div>
  );
}


export default App;