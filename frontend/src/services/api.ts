import axios from "axios";

import type {
  ChatRequest,
  ChatResponse,
} from "../types/chat";


const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});


export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>(
    "/api/chat",
    request
  );

  return response.data;
}


/* =====================================================
 * INVESTIGATION STREAM
 * ===================================================== */

export interface InvestigationStreamEvent {
  type:
    | "investigation_started"
    | "plan"
    | "hypotheses"
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

  const response = await fetch(
    "http://127.0.0.1:8000/api/investigate/stream",
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

  const response = await fetch(
    "http://127.0.0.1:8000/api/investigate/challenge/stream",
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