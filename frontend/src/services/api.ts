import axios from "axios";

import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  CreateConversationRequest,
  RenameConversationRequest,
} from "../types/chat";


const API_BASE_URL =
  "http://127.0.0.1:8000";


const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});


/* =====================================================
 * STANDARD COPILOT CHAT
 * ===================================================== */

export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {

  const response =
    await api.post<ChatResponse>(
      "/api/chat",
      request
    );

  return response.data;
}


/* =====================================================
 * CONVERSATIONS
 * ===================================================== */

export async function createConversation(
  request: CreateConversationRequest = {}
): Promise<Conversation> {

  const response =
    await api.post<Conversation>(
      "/api/conversations",
      request
    );

  return response.data;
}


export async function listConversations(
  includeArchived = false
): Promise<ConversationSummary[]> {

  const response =
    await api.get<ConversationSummary[]>(
      "/api/conversations",
      {
        params: {
          include_archived:
            includeArchived,
        },
      }
    );

  return response.data;
}


export async function getConversation(
  conversationId: string
): Promise<Conversation> {

  const response =
    await api.get<Conversation>(
      `/api/conversations/${conversationId}`
    );

  return response.data;
}


export async function renameConversation(
  conversationId: string,
  request: RenameConversationRequest
): Promise<ConversationSummary> {

  const response =
    await api.patch<ConversationSummary>(
      `/api/conversations/${conversationId}`,
      request
    );

  return response.data;
}


export async function archiveConversation(
  conversationId: string
): Promise<ConversationSummary> {

  const response =
    await api.post<ConversationSummary>(
      `/api/conversations/${conversationId}/archive`
    );

  return response.data;
}


export async function unarchiveConversation(
  conversationId: string
): Promise<ConversationSummary> {

  const response =
    await api.post<ConversationSummary>(
      `/api/conversations/${conversationId}/unarchive`
    );

  return response.data;
}


export async function deleteConversation(
  conversationId: string
): Promise<void> {

  await api.delete(
    `/api/conversations/${conversationId}`
  );
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
    | "answer_start"
    | "token"
    | "answer_end"
    | "error";

  data?: unknown;
}


export async function streamInvestigation(
  request: ChatRequest,
  onEvent: (
    event: InvestigationStreamEvent
  ) => void
): Promise<void> {

  const response =
    await fetch(
      `${API_BASE_URL}/api/investigate/stream`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(request),
      }
    );


  if (!response.ok) {
    throw new Error(
      `Investigation request failed: ${response.status}`
    );
  }


  if (!response.body) {
    throw new Error(
      "Streaming response body is unavailable."
    );
  }


  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder();

  let buffer = "";


  while (true) {

    const {
      value,
      done,
    } = await reader.read();


    if (done) {
      break;
    }


    buffer += decoder.decode(
      value,
      {
        stream: true,
      }
    );


    const lines =
      buffer.split("\n");


    buffer =
      lines.pop() || "";


    for (const line of lines) {

      if (!line.trim()) {
        continue;
      }


      const parsed =
        JSON.parse(line);


      const event =
        parsed as InvestigationStreamEvent;


      onEvent(event);
    }
  }


  /*
   * The final chunk may not end with a newline.
   * Process whatever remains in the buffer.
   */

  if (buffer.trim()) {

    const parsed =
      JSON.parse(buffer);


    const event =
      parsed as InvestigationStreamEvent;


    onEvent(event);
  }
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
    | "error";

  data?: unknown;
}


export async function streamChallenge(
  request: ChatRequest,
  onEvent: (
    event: ChallengeStreamEvent
  ) => void
): Promise<void> {

  const response =
    await fetch(
      `${API_BASE_URL}/api/investigate/challenge/stream`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(request),
      }
    );


  if (!response.ok) {
    throw new Error(
      `Challenge request failed: ${response.status}`
    );
  }


  if (!response.body) {
    throw new Error(
      "Challenge streaming response body is unavailable."
    );
  }


  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder();

  let buffer = "";


  while (true) {

    const {
      value,
      done,
    } = await reader.read();


    if (done) {
      break;
    }


    buffer += decoder.decode(
      value,
      {
        stream: true,
      }
    );


    const lines =
      buffer.split("\n");


    buffer =
      lines.pop() || "";


    for (const line of lines) {

      if (!line.trim()) {
        continue;
      }


      const parsed =
        JSON.parse(line);


      const event =
        parsed as ChallengeStreamEvent;


      onEvent(event);
    }
  }


  /*
   * The final chunk may not end with a newline.
   * Process whatever remains in the buffer.
   */

  if (buffer.trim()) {

    const parsed =
      JSON.parse(buffer);


    const event =
      parsed as ChallengeStreamEvent;


    onEvent(event);
  }
}