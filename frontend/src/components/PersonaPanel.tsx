import type { PersonaMessage } from "../types";

interface Props {
  personaId: string;
  messages: PersonaMessage[];
}

const PERSONA_COLOR_VARS: Record<string, string> = {
  investor: "var(--investor)",
  customer: "var(--customer)",
  regulator: "var(--regulator)",
};

export function PersonaPanel({ personaId, messages }: Props) {
  const color = PERSONA_COLOR_VARS[personaId];

  return (
    <div
      className="card persona-panel"
      style={color ? ({ "--persona-color": color } as React.CSSProperties) : undefined}
    >
      <div className="persona-panel-head">
        <span className="persona-dot" />
        <h3>{personaId}</h3>
      </div>
      {messages.map((m, i) =>
        m.role === "user" ? (
          <p key={i} className="msg msg-user">
            <span className="msg-user-label">You</span>
            {m.content}
          </p>
        ) : (
          <p key={i} className="msg">
            {m.content}
          </p>
        )
      )}
    </div>
  );
}
