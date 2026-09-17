export interface PersonaMessage {
  role: "persona" | "user";
  content: string;
}

export interface ChallengeLogEntry {
  persona_id: string;
  challenge_text: string;
  response_text: string;
  outcome: "held" | "conceded";
}

export interface Synthesis {
  agreement: string[];
  divergence: string[];
  biggest_risk: string;
}

export type InterruptPayload =
  | { type: "present_findings"; persona_threads: Record<string, PersonaMessage[]> }
  | { type: "human_approval_gate"; challenge_log: ChallengeLogEntry[] }
  | null;

export interface RunState {
  thread_id: string;
  next_nodes: string[];
  round_count: number | null;
  human_approval: "pending" | "approved" | "rejected" | null;
  persona_threads: Record<string, PersonaMessage[]>;
  challenge_log: ChallengeLogEntry[];
  synthesis: Synthesis | null;
  interrupt: InterruptPayload;
}
