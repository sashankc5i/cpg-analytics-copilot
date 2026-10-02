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


export type ChatMessageType = 
  | "normal" 
  | "challenge"; 


export interface EvidenceReference { 
  investigation: string; 
  field: string; 
  entity: string | null; 
} 


export interface InvestigationClaim { 
  id: string; 
  statement: string; 
  status: string; 
  evidence_refs: EvidenceReference[]; 
  traceability_status: string; 
} 


export type InvestigationEvidence = Record< 
  string, 
  unknown 
>; 


export interface EvidenceGraphNode {
  id: string;
  type: "claim" | "evidence" | "metric" | "hypothesis" | string;
  label: string;
  data: Record<string, unknown> | unknown;
}


export interface EvidenceGraphEdge {
  source: string;
  target: string;
  type: "supported_by" | "tested_by" | string;
}


export interface EvidenceGraph {
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
} 


export interface InvestigationConfidence { 
  score: number; 
  level: "high" | "moderate" | "low" | string; 
  basis: string; 
  signals: { 
    investigation_coverage: number; 
    hypothesis_evidence_coverage: number; 
    claim_traceability: number; 
    evidence_breadth: number; 
  }; 
  counts: { 
    planned_investigations: number; 
    evidence_sources: number; 
    hypotheses: number; 
    claims: number; 
    traceable_claims: number; 
  }; 
  limitations: string[]; 
} 


export interface ChatMessage { 
  role: "user" | "assistant"; 
  content: string; 
  toolsUsed?: string[]; 
  visualization?: Visualization | null; 
  claims?: InvestigationClaim[]; 
  investigationEvidence?: InvestigationEvidence; 
  confidence?: InvestigationConfidence; 
  evidenceGraph?: EvidenceGraph;
  messageType?: ChatMessageType; 
} 


/* ===================================================== 
 * CONVERSATION 
 * ===================================================== */ 

export interface Conversation { 
  conversation_id: string; 
  title: string; 
  created_at: string; 
  updated_at: string; 
  archived: boolean; 
  history: ChatMessage[]; 
} 


export interface ConversationSummary { 
  conversation_id: string; 
  title: string; 
  created_at: string; 
  updated_at: string; 
  archived: boolean; 
} 


export interface CreateConversationRequest { 
  conversation_id?: string; 
  title?: string; 
} 


export interface RenameConversationRequest { 
  title: string; 
}