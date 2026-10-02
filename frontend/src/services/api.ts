
import axios from "axios";

import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  CreateConversationRequest,
  RenameConversationRequest,
} from "../types/chat";

/* =====================================================
 * API CONFIGURATION
 * ===================================================== */

const API_BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/* =====================================================
 * HELPERS
 * ===================================================== */

/**
 * Extract a useful error message from Axios/fetch errors.
 */
function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;

    if (typeof data === "string") {
      return data;
    }

    if (
      data &&
      typeof data === "object" &&
      "detail" in data &&
      typeof data.detail === "string"
    ) {
      return data.detail;
    }

    if (
      data &&
      typeof data === "object" &&
      "message" in data &&
      typeof data.message === "string"
    ) {
      return data.message;
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unexpected API error occurred.";
}

/**
 * Safely parse a JSON line coming from a streaming endpoint.
 */
function parseStreamLine<T>(line: string): T | null {
  const trimmed = line.trim();

  if (!trimmed) {
    return null;
  }

  try {
    return JSON.parse(trimmed) as T;
  } catch (error) {
    console.error("Failed to parse streaming event:", {
      line: trimmed,
      error,
    });

    return null;
  }
}

/**
 * Generic NDJSON streaming reader.
 *
 * Backend is expected to return one JSON object per line.
 */
async function readJsonStream<T>(
  response: Response,
  onEvent: (event: T) => void
): Promise<void> {
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, {
        stream: true,
      });

      const lines = buffer.split("\n");

      /*
       * Keep the final incomplete line in the buffer.
       */
      buffer = lines.pop() || "";

      for (const line of lines) {
        const event = parseStreamLine<T>(line);

        if (event !== null) {
          onEvent(event);
        }
      }
    }

    /*
     * Flush any remaining decoder bytes.
     */
    buffer += decoder.decode();

    /*
     * The final event may not have ended with \n.
     */
    if (buffer.trim()) {
      const event = parseStreamLine<T>(buffer);

      if (event !== null) {
        onEvent(event);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/* =====================================================
 * STANDARD COPILOT CHAT
 * ===================================================== */

export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  try {
    const response = await api.post<ChatResponse>(
      "/api/chat",
      request
    );

    return response.data;
  } catch (error) {
    console.error("sendMessage failed:", error);

    throw new Error(
      `Failed to send message: ${getErrorMessage(error)}`
    );
  }
}

/* =====================================================
 * CONVERSATIONS
 * ===================================================== */

/**
 * Create a new conversation.
 *
 * If no name/title is supplied, the backend should generate
 * the initial conversation metadata.
 */
export async function createConversation(
  request: CreateConversationRequest = {}
): Promise<Conversation> {
  try {
    const response = await api.post<Conversation>(
      "/api/conversations",
      request
    );

    return response.data;
  } catch (error) {
    console.error("createConversation failed:", error);

    throw new Error(
      `Failed to create conversation: ${getErrorMessage(error)}`
    );
  }
}

/**
 * Rename an existing conversation.
 *
 * IMPORTANT:
 * The backend response is returned directly.
 * This prevents the frontend from accidentally replacing
 * the renamed conversation with stale conversation data.
 */
export async function renameConversation(
  conversationId: string,
  request: RenameConversationRequest
): Promise<ConversationSummary> {
  if (!conversationId) {
    throw new Error("Conversation ID is required.");
  }

  if (!request) {
    throw new Error("Rename request is required.");
  }

  try {
    const response = await api.patch<ConversationSummary>(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}`,
      request
    );

    return response.data;
  } catch (error) {
    console.error("renameConversation failed:", error);

    throw new Error(
      `Failed to rename conversation: ${getErrorMessage(error)}`
    );
  }
}

/**
 * List conversations.
 */
export async function listConversations(
  includeArchived = false
): Promise<ConversationSummary[]> {
  try {
    const response = await api.get<ConversationSummary[]>(
      "/api/conversations",
      {
        params: {
          include_archived: includeArchived,
        },
      }
    );

    return response.data;
  } catch (error) {
    console.error("listConversations failed:", error);

    throw new Error(
      `Failed to load conversations: ${getErrorMessage(error)}`
    );
  }
}

/**
 * Get one complete conversation.
 */
export async function getConversation(
  conversationId: string
): Promise<Conversation> {
  if (!conversationId) {
    throw new Error("Conversation ID is required.");
  }

  try {
    const response = await api.get<Conversation>(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}`
    );

    return response.data;
  } catch (error) {
    console.error("getConversation failed:", error);

    throw new Error(
      `Failed to load conversation: ${getErrorMessage(error)}`
    );
  }
}

/**
 * Archive a conversation.
 */
export async function archiveConversation(
  conversationId: string
): Promise<ConversationSummary> {
  if (!conversationId) {
    throw new Error("Conversation ID is required.");
  }

  try {
    const response = await api.post<ConversationSummary>(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}/archive`
    );

    return response.data;
  } catch (error) {
    console.error("archiveConversation failed:", error);

    throw new Error(
      `Failed to archive conversation: ${getErrorMessage(error)}`
    );
  }
}

/**
 * Unarchive a conversation.
 */
export async function unarchiveConversation(
  conversationId: string
): Promise<ConversationSummary> {
  if (!conversationId) {
    throw new Error("Conversation ID is required.");
  }

  try {
    const response = await api.post<ConversationSummary>(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}/unarchive`
    );

    return response.data;
  } catch (error) {
    console.error("unarchiveConversation failed:", error);

    throw new Error(
      `Failed to unarchive conversation: ${getErrorMessage(error)}`
    );
  }
}

/**
 * Permanently delete a conversation.
 */
export async function deleteConversation(
  conversationId: string
): Promise<void> {
  if (!conversationId) {
    throw new Error("Conversation ID is required.");
  }

  try {
    await api.delete(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}`
    );
  } catch (error) {
    console.error("deleteConversation failed:", error);

    throw new Error(
      `Failed to delete conversation: ${getErrorMessage(error)}`
    );
  }
}

/* =====================================================
 * INVESTIGATION STREAM
 * ===================================================== */

export interface InvestigationStreamEvent {
  type:
    | "investigation_started"
    | "plan"
    | "hypotheses"
    | "claims"
    | "evidence"
    | "confidence"
    | "evidence_graph"
    | "answer_start"
    | "token"
    | "answer_end"
    | "error"
    | string;

  data?: unknown;
}

/**
 * Stream an investigation.
 *
 * Backend endpoint:
 * POST /api/investigate/stream
 *
 * Expected format:
 * {"type":"investigation_started","data":...}
 * {"type":"plan","data":...}
 * {"type":"token","data":...}
 * ...
 */
export async function streamInvestigation(
  request: ChatRequest,
  onEvent: (event: InvestigationStreamEvent) => void
): Promise<void> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/investigate/stream`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(request),
      }
    );
  } catch (error) {
    console.error("streamInvestigation network error:", error);

    throw new Error(
      `Unable to connect to investigation API: ${
        error instanceof Error
          ? error.message
          : "Network error"
      }`
    );
  }

  if (!response.ok) {
    let detail = "";

    try {
      detail = await response.text();
    } catch {
      // Ignore response parsing failure.
    }

    throw new Error(
      `Investigation request failed: ${response.status}${
        detail ? ` - ${detail}` : ""
      }`
    );
  }

  await readJsonStream<InvestigationStreamEvent>(
    response,
    onEvent
  );
}

/* =====================================================
 * CHALLENGE STREAM
 * ===================================================== */

export interface ChallengeStreamEvent {
  type:
    | "challenge_started"
    | "claims"
    | "challenge_plan"
    | "challenge_evidence"
    | "answer_start"
    | "token"
    | "answer_end"
    | "error"
    | string;

  data?: unknown;
}

/**
 * Stream a challenge/investigation challenge.
 *
 * Backend endpoint:
 * POST /api/investigate/challenge/stream
 */
export async function streamChallenge(
  request: ChatRequest,
  onEvent: (event: ChallengeStreamEvent) => void
): Promise<void> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/investigate/challenge/stream`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(request),
      }
    );
  } catch (error) {
    console.error("streamChallenge network error:", error);

    throw new Error(
      `Unable to connect to challenge API: ${
        error instanceof Error
          ? error.message
          : "Network error"
      }`
    );
  }

  if (!response.ok) {
    let detail = "";

    try {
      detail = await response.text();
    } catch {
      // Ignore response parsing failure.
    }

    throw new Error(
      `Challenge request failed: ${response.status}${
        detail ? ` - ${detail}` : ""
      }`
    );
  }

  await readJsonStream<ChallengeStreamEvent>(
    response,
    onEvent
  );
}

