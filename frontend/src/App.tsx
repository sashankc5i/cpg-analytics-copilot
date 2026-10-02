import {
  useEffect,
  useRef,
  useState,
} from "react";

import ChatWindow from "./components/ChatWindow";

import {
  createConversation,
  getConversation,
  listConversations,
  sendMessage,
  streamChallenge,
  streamInvestigation,
  type ChallengeStreamEvent,
  type InvestigationStreamEvent,
} from "./services/api";

import type {
  ChatMessage,
  ConversationSummary,
  InvestigationClaim,
  InvestigationEvidence,
} from "./types/chat";


type WorkspaceMode =
  | "copilot"
  | "investigate";


/* =====================================================
 * BRAND
 * ===================================================== */

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


/* =====================================================
 * SIDEBAR ICON
 * ===================================================== */

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


/* =====================================================
 * APP
 * ===================================================== */

function App() {

  /*
   * ------------------------------------------------
   * CONVERSATION STATE
   * ------------------------------------------------
   *
   * One conversation is shared by the entire workspace.
   *
   * Copilot
   * Investigation
   * Challenge
   *
   * all operate against the same conversation ID.
   */

  const [
    activeConversationId,
    setActiveConversationId,
  ] = useState<string | null>(null);


  const [
    conversations,
    setConversations,
  ] = useState<ConversationSummary[]>([]);


  const [
    conversationLoading,
    setConversationLoading,
  ] = useState(true);

  /*
   * React StrictMode intentionally runs effects twice in development.
   * The initialization guard prevents that second effect pass from
   * creating a duplicate "New Chat" conversation.
   */
  const initializationStartedRef = useRef(false);


  /*
   * ------------------------------------------------
   * MESSAGE STATE
   * ------------------------------------------------
   *
   * Messages now represent the active conversation,
   * rather than separate Copilot and Investigation
   * histories.
   */

  const [
    messages,
    setMessages,
  ] = useState<ChatMessage[]>([]);


  /*
   * ------------------------------------------------
   * COMPOSER STATE
   * ------------------------------------------------
   */

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
   * INVESTIGATION STATE
   * ------------------------------------------------
   *
   * This is intentionally UI state.
   *
   * The authoritative investigation memory lives
   * in the backend InvestigationSessionManager.
   */

  const [
    investigationHasConclusion,
    setInvestigationHasConclusion,
  ] = useState(false);


  /*
   * ------------------------------------------------
   * LOAD CONVERSATIONS ON STARTUP
   * ------------------------------------------------
   */

  useEffect(() => {

    if (initializationStartedRef.current) {
      return;
    }

    initializationStartedRef.current = true;

    async function initializeConversation() {

      try {

        setConversationLoading(true);
        setError(null);


        const existing =
          await listConversations();


        /*
         * If conversations already exist,
         * load the most recently updated one.
         */

        if (existing.length > 0) {

          const latest =
            existing[0];

          setConversations(existing);

          await loadConversation(
            latest.conversation_id
          );

          return;
        }


        /*
         * No conversations exist.
         *
         * Create the first one.
         */

        const created =
          await createConversation({
            title: "New Chat",
          });


        setConversations([
          {
            conversation_id:
              created.conversation_id,

            title:
              created.title,

            created_at:
              created.created_at,

            updated_at:
              created.updated_at,

            archived:
              created.archived,
          },
        ]);


        setActiveConversationId(
          created.conversation_id
        );


        setMessages(
          created.history || []
        );


      } catch (err) {

        console.error(err);

        setError(
          "Unable to load conversations. Check that the API is running."
        );

      } finally {

        setConversationLoading(false);
      }
    }


    initializeConversation();

  }, []);


  /*
   * ------------------------------------------------
   * LOAD A CONVERSATION
   * ------------------------------------------------
   */

  async function loadConversation(
    conversationId: string
  ) {

    try {

      setConversationLoading(true);
      setError(null);


      const conversation =
        await getConversation(
          conversationId
        );


      setActiveConversationId(
        conversation.conversation_id
      );


      setMessages(
        conversation.history || []
      );


      /*
       * Determine whether the currently loaded
       * conversation contains an assistant response.
       *
       * This gives the Investigation workspace a
       * reasonable initial state.
       *
       * The backend remains the authoritative source
       * for challenge eligibility.
       */

      const hasAssistantMessage =
        conversation.history.some(
          (message) =>
            message.role === "assistant" &&
            message.content.trim().length > 0
        );


      setInvestigationHasConclusion(
        hasAssistantMessage
      );


    } catch (err) {

      console.error(err);

      setError(
        "Unable to load the selected conversation."
      );

    } finally {

      setConversationLoading(false);
    }
  }


  /*
   * ------------------------------------------------
   * CREATE NEW CHAT
   * ------------------------------------------------
   */

  async function handleNewConversation() {

    if (loading) {
      return;
    }


    try {

      setError(null);
      setConversationLoading(true);


      const conversation =
        await createConversation({
          title: "New Chat",
        });


      const summary: ConversationSummary = {
        conversation_id:
          conversation.conversation_id,

        title:
          conversation.title,

        created_at:
          conversation.created_at,

        updated_at:
          conversation.updated_at,

        archived:
          conversation.archived,
      };


      setConversations(
        (previous) => [
          summary,
          ...previous.filter(
            (item) =>
              item.conversation_id !==
              summary.conversation_id
          ),
        ]
      );


      setActiveConversationId(
        conversation.conversation_id
      );


      setMessages(
        conversation.history || []
      );


      setInvestigationHasConclusion(
        false
      );


      setMode("copilot");


    } catch (err) {

      console.error(err);

      setError(
        "Unable to create a new conversation."
      );

    } finally {

      setConversationLoading(false);
    }
  }


  /*
   * ------------------------------------------------
   * UPDATE LOCAL CONVERSATION LIST
   * ------------------------------------------------
   *
   * The backend updates updated_at whenever a
   * conversation receives a message.
   *
   * We update the frontend list after a successful
   * response so the current conversation remains
   * visible.
   */

  function touchActiveConversation(
    conversationId: string
  ) {

    setConversations(
      (previous) => {

        const existing =
          previous.find(
            (item) =>
              item.conversation_id ===
              conversationId
          );


        if (!existing) {
          return previous;
        }


        const updated: ConversationSummary = {
          ...existing,
          updated_at:
            new Date().toISOString(),
        };


        return [
          updated,
          ...previous.filter(
            (item) =>
              item.conversation_id !==
              conversationId
          ),
        ];
      }
    );
  }


  /*
   * ------------------------------------------------
   * MESSAGE HELPERS
   * ------------------------------------------------
   */

  function addMessage(
    message: ChatMessage
  ) {

    setMessages(
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


    if (
      !message ||
      loading ||
      conversationLoading
    ) {
      return;
    }


    if (!activeConversationId) {

      setError(
        "No active conversation is available."
      );

      return;
    }


    setError(null);


    /*
     * Add the user's message immediately so
     * the interface feels responsive.
     */

    addMessage({
      role: "user",
      content: message,
    });


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
              activeConversationId,
          });


        addMessage({
          role: "assistant",
          content:
            response.answer,

          toolsUsed:
            response.tools_used,

          visualization:
            response.visualization,
        });


        touchActiveConversation(
          activeConversationId
        );


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

    let investigationClaims: InvestigationClaim[] =
      [];

    let investigationEvidence: InvestigationEvidence =
      {};


    try {

      await streamInvestigation(
        {
          message,
          conversation_id:
            activeConversationId,
        },

        (
          event: InvestigationStreamEvent
        ) => {

          if (event.type === "claims") {
            investigationClaims =
              Array.isArray(event.data)
                ? event.data as InvestigationClaim[]
                : [];
          }

          if (event.type === "evidence") {
            investigationEvidence =
              event.data &&
              typeof event.data === "object"
                ? event.data as InvestigationEvidence
                : {};
          }

          handleInvestigationEvent(
            event,
            assistantMessageCreated,
            () => {
              assistantMessageCreated =
                true;
            },
            () => investigationClaims,
            () => investigationEvidence
          );
        }
      );


      /*
       * A successful investigation means the
       * conversation now has an investigation
       * conclusion that can be challenged.
       */

      setInvestigationHasConclusion(
        true
      );


      touchActiveConversation(
        activeConversationId
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
    markAssistantCreated: () => void,
    getClaims: () => InvestigationClaim[],
    getEvidence: () => InvestigationEvidence
  ) {

    if (
      event.type ===
      "investigation_started"
    ) {
      return;
    }


    /*
     * Plan and hypotheses are internal workflow
     * information.
     *
     * The final synthesis incorporates them.
     */

    if (
      event.type === "plan" ||
      event.type === "hypotheses"
    ) {
      return;
    }


    /*
     * Claims and evidence are structured trust
     * metadata. They are kept out of the streamed
     * prose and attached to the final assistant
     * message for user inspection.
     */
    if (
      event.type === "claims" ||
      event.type === "evidence"
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

        addMessage({
          role: "assistant",
          content: "",
          messageType: "normal",
          claims: getClaims(),
          investigationEvidence: getEvidence(),
        });


        markAssistantCreated();
      }


      return;
    }


    /*
     * Append streamed tokens to the investigation
     * assistant message.
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

        addMessage({
          role: "assistant",
          content: token,
          messageType: "normal",
          claims: getClaims(),
          investigationEvidence: getEvidence(),
        });


        markAssistantCreated();

        return;
      }


      setMessages(
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
           * investigation message.
           */

          if (
            lastMessage.role !==
            "assistant"
          ) {

            updated.push({
              role: "assistant",
              content: token,
              messageType: "normal",
              claims: getClaims(),
              investigationEvidence: getEvidence(),
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
      !investigationHasConclusion ||
      !activeConversationId
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
           * The backend retrieves the latest
           * investigation from server-side
           * investigation memory.
           */

          message:
            "Challenge my conclusion",

          conversation_id:
            activeConversationId,
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
     * The challenge must never be appended to the
     * original investigation conclusion.
     */

    if (
      event.type ===
      "answer_start"
    ) {

      if (
        !challengeMessageCreated
      ) {

        addMessage({
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

        addMessage({
          role: "assistant",
          content: token,
          messageType: "challenge",
        });


        markChallengeCreated();

        return;
      }


      setMessages(
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
          CONVERSATIONS
        </div>


        <button
          type="button"
          className="nav-item"
          onClick={
            handleNewConversation
          }
          disabled={
            loading ||
            conversationLoading
          }
        >

          <SidebarIcon type="chat" />

          <span>
            New Chat
          </span>

        </button>


        <div className="conversation-list">

          {conversations.map(
            (conversation) => (

              <button
                key={
                  conversation.conversation_id
                }
                type="button"
                className={`conversation-item ${
                  activeConversationId ===
                  conversation.conversation_id
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  loadConversation(
                    conversation.conversation_id
                  )
                }
                disabled={
                  loading ||
                  conversationLoading
                }
              >

                <span className="conversation-title">
                  {conversation.title}
                </span>

              </button>

            )
          )}

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
            disabled={
              loading ||
              conversationLoading
            }
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
            disabled={
              loading ||
              conversationLoading
            }
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
              loading={
                loading ||
                conversationLoading
              }
              mode={mode}
            />


            {/*
             * ------------------------------------------------
             * CHALLENGE ACTION
             * ------------------------------------------------
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
                    disabled={
                      loading ||
                      conversationLoading
                    }
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


            {messages.length === 0 &&
              !conversationLoading && (
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
              onSubmit={
                handleSubmit
              }
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
                disabled={
                  loading ||
                  conversationLoading
                }
                aria-label="Business question"
              />


              <button
                type="submit"
                disabled={
                  loading ||
                  conversationLoading ||
                  !input.trim() ||
                  !activeConversationId
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