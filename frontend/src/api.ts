import type { RunState } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request(path: string, options?: RequestInit): Promise<RunState> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

export function startRun(pitch: string): Promise<RunState> {
  return request("/runs", { method: "POST", body: JSON.stringify({ pitch }) });
}

export function getRun(threadId: string): Promise<RunState> {
  return request(`/runs/${threadId}`);
}

export function challengeRun(
  threadId: string,
  personaId: string,
  text: string
): Promise<RunState> {
  return request(`/runs/${threadId}/challenge`, {
    method: "POST",
    body: JSON.stringify({ persona_id: personaId, text }),
  });
}

export function doneRun(threadId: string): Promise<RunState> {
  return request(`/runs/${threadId}/done`, { method: "POST" });
}

export function approveRun(threadId: string): Promise<RunState> {
  return request(`/runs/${threadId}/approve`, { method: "POST" });
}

export function rejectRun(threadId: string): Promise<RunState> {
  return request(`/runs/${threadId}/reject`, { method: "POST" });
}
