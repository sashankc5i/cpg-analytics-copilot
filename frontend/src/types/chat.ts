export interface ToolResult {
  tool: string;
  result: unknown;
}


export interface Visualization {
  type: "line" | "bar" | string | null;
  title: string | null;
  x: unknown[];
  y: unknown[];
}


export interface ChatRequest {
  message: string;
  conversation_id: string;
}


export interface ChatResponse {
  answer: string;
  tools_used: string[];
  tool_results: ToolResult[];
  visualization: Visualization | null;
  conversation_id: string;
}


export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  visualization?: Visualization | null;
}