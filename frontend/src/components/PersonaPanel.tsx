import type { PersonaMessage } from "../types";

interface Props {
  personaId: string;
  messages: PersonaMessage[];
}

export function PersonaPanel({ personaId, messages }: Props) {
  return (
    <div className="persona-panel">
      <h3>{personaId}</h3>
      {messages.map((m, i) => (
        <p key={i} className={m.role === "user" ? "msg msg-user" : "msg"}>
          {m.role === "user" ? "You: " : ""}
          {m.content}
        </p>
      ))}
    </div>
  );
}
